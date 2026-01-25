#pragma once

#include <string>
#include <map>
#include <functional>
#include <nlohmann/json.hpp>
#include <memory>

using json = nlohmann::json;

namespace pswallet
{

    /**
     * Script execution context for smart contracts
     */
    class ScriptContext
    {
    public:
        /**
         * Create execution context
         * @param wallet_address Executing wallet address
         * @param contract_address Contract address
         */
        ScriptContext(const std::string &wallet_address,
                      const std::string &contract_address);

        /**
         * Register a native function
         * @param name Function name
         * @param func Callable function
         */
        void register_function(const std::string &name,
                               std::function<json(const json &)> func);

        /**
         * Get context variable
         * @param key Variable name
         * @return Variable value or null
         */
        json get_variable(const std::string &key) const;

        /**
         * Set context variable
         * @param key Variable name
         * @param value Variable value
         */
        void set_variable(const std::string &key, const json &value);

        /**
         * Get wallet address
         */
        const std::string &get_wallet_address() const { return wallet_address_; }

        /**
         * Get contract address
         */
        const std::string &get_contract_address() const { return contract_address_; }

        /**
         * Get all registered functions
         */
        const std::map<std::string, std::function<json(const json &)>> &
        get_functions() const { return functions_; }

        /**
         * Get all context variables
         * @return Map of all variables
         */
        const std::map<std::string, json> &get_variables() const { return variables_; }

        /**
         * Get complete context state
         * @return JSON object containing all variables
         */
        json get_state() const
        {
            return json(variables_);
        }

    private:
        std::string wallet_address_;
        std::string contract_address_;
        std::map<std::string, json> variables_;
        std::map<std::string, std::function<json(const json &)>> functions_;
    };

    /**
     * Smart contract script executor
     */
    class SmartContractEngine
    {
    public:
        /**
         * Execute a script file
         * @param script_file Path to .ps (PiScript) file
         * @param context Execution context
         * @return Execution result as JSON
         */
        static json execute_file(const std::string &script_file,
                                 const std::shared_ptr<ScriptContext> &context);

        /**
         * Execute inline script
         * @param script_code Script source code
         * @param context Execution context
         * @return Execution result as JSON
         */
        static json execute(const std::string &script_code,
                            const std::shared_ptr<ScriptContext> &context);

        /**
         * Validate script syntax
         * @param script_code Script source code
         * @return Error message or empty if valid
         */
        static std::string validate_script(const std::string &script_code);

        /**
         * Get available built-in functions
         * @return List of function names
         */
        static std::vector<std::string> get_builtin_functions();

    private:
        /**
         * Parse and execute script AST
         * @param script_code Script to parse
         * @param context Execution context
         * @return Execution result
         */
        static json execute_ast(const std::string &script_code,
                                const std::shared_ptr<ScriptContext> &context);

        /**
         * Execute a transaction instruction
         * @param instruction Transaction instruction
         * @param context Execution context
         * @return Transaction result
         */
        static json execute_transaction(const json &instruction,
                                        const std::shared_ptr<ScriptContext> &context);

        /**
         * Execute a contract call
         * @param call_data Function call data
         * @param context Execution context
         * @return Call result
         */
        static json execute_call(const json &call_data,
                                 const std::shared_ptr<ScriptContext> &context);

        /**
         * Sandbox enforcement - verify script doesn't exceed limits
         * @param script_code Script to check
         * @return Error message or empty if safe
         */
        static std::string check_sandbox_constraints(const std::string &script_code);
    };

    /**
     * PiScript language spec
     *
     * Example smart contract script (.ps file):
     *
     * // Payments smart contract
     * contract Payment {
     *     const recipient = "0x1234...";
     *     const amount = 100.0;
     *
     *     function execute() {
     *         transaction transfer {
     *             to: recipient,
     *             amount: amount,
     *             type: "token_transfer"
     *         }
     *         return "Payment sent";
     *     }
     * }
     *
     * // Multi-step escrow
     * contract Escrow {
     *     state amount = 0;
     *     state locked = false;
     *
     *     function lock(value) {
     *         amount = value;
     *         locked = true;
     *         return "Funds locked";
     *     }
     *
     *     function release() {
     *         if (!locked) return error("Not locked");
     *
     *         transaction transfer {
     *             to: this.beneficiary,
     *             amount: amount,
     *             type: "token_transfer"
     *         }
     *         locked = false;
     *         return "Funds released";
     *     }
     * }
     */

} // namespace pswallet
