#include "pisecured/daemon.hpp"
#include "pisecured/chain_rpc.hpp"
#include "release_update.hpp"
#include <iostream>
#include <csignal>

namespace pisecured
{
    Daemon::Daemon(const Config &cfg)
        : config_(cfg)
    {
        // Initialize validator bucket if enabled (legacy purse naming supported)
        // Note: Bucket is created regardless of mode (--validate-only or normal mining)
        // because pisecured validates blocks in both modes
        if (cfg.validator_rewards_enabled)
        {
            try
            {
                validator_purse_ = std::make_unique<ValidatorPurse>(
                    cfg.validator_bucket_path.string(),
                    cfg.validator_rewards_percentage);
                std::cout << "Validator bucket initialized at "
                          << cfg.validator_bucket_path << std::endl;
                std::cout << "Current balance: "
                          << validator_purse_->get_balance() << " 314ST" << std::endl;

                // Link wallet if configured
                if (!cfg.validator_wallet_address.empty())
                {
                    if (validator_purse_->link_wallet(cfg.validator_wallet_address))
                    {
                        std::cout << "Bucket linked to wallet: " << cfg.validator_wallet_address << std::endl;
                    }
                    else
                    {
                        std::cerr << "Failed to link wallet: " << cfg.validator_wallet_address << std::endl;
                    }
                }
            }
            catch (const std::exception &e)
            {
                std::cerr << "Failed to initialize validator bucket: "
                          << e.what() << std::endl;
                validator_purse_ = nullptr;
            }
        }
    }

    Daemon::~Daemon()
    {
        stop();
    }

    bool Daemon::start()
    {
        if (running_.exchange(true))
        {
            return false;
        }

        if (!storage_.init(config_.datadir, config_.testnet, config_.hybrid_storage))
        {
            std::cerr << "Storage init failed\n";
            running_ = false;
            return false;
        }
        if (!restore_chain(storage_))
        {
            std::cerr << "Chain restore failed\n";
            running_ = false;
            return false;
        }

        if (!p2p_.start(config_, &storage_))
        {
            std::cerr << "P2P start failed\n";
            running_ = false;
            return false;
        }

        // Phase 3: Prefer WebSocket server; start HTTP RPC only if enabled
        if (config_.ws_enabled)
        {
            if (!ws_.start(config_, &storage_, &p2p_, validator_purse_.get()))
            {
                std::cerr << "WebSocket server start failed\n";
            }
        }
        if (config_.http_enabled)
        {
            if (!rpc_.start(config_, &storage_, &p2p_, validator_purse_.get(), p2p_.getThreatDetector()))
            {
                std::cerr << "RPC start failed\n";
                running_ = false;
                return false;
            }
        }

        check_for_update();
        return true;
    }

    void Daemon::check_for_update()
    {
        if (config_.no_update_check)
        {
            return;
        }
        try
        {
            const auto report = pisecure_update::check_release(PISECURE_RELEASE);
            if (report.kind != pisecure_update::Report::Kind::Newer)
            {
                std::cout << report.line << std::endl;
                return;
            }
            pisecure_update::write_available((config_.datadir / "update-available.json").string(), report);
            if (!config_.apply_update)
            {
                std::cout << report.line << std::endl;
                return;
            }
            std::string err;
            if (!pisecure_update::apply_daemon(report, err))
            {
                std::cout << err << std::endl;
                return;
            }
            std::cout << "update applied " << report.tag << std::endl;
            if (!pisecure_update::restart_after_apply(err))
            {
                std::cout << err << std::endl;
            }
        }
        catch (const std::exception &)
        {
            std::cout << "update check skipped" << std::endl;
        }
    }

    void Daemon::stop()
    {
        if (!running_.exchange(false))
        {
            return;
        }

        rpc_.stop();
        ws_.stop();
        p2p_.stop();
        // Storage flush would go here if needed
    }
}
