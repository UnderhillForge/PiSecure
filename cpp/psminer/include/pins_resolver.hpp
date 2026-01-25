#pragma once

#include <string>
#include <optional>
#include <map>
#include <cstdint>

namespace psminer
{

    /**
     * PiNS (Pi Name System) Resolver
     * Resolves user-friendly PiNS names to blockchain wallet addresses
     */
    class PiNSResolver
    {
    public:
        /**
         * Create resolver with blockchain node URL
         * @param node_url Blockchain REST API URL (e.g., http://localhost:3142)
         */
        explicit PiNSResolver(const std::string &node_url);

        /**
         * Resolve a PiNS name to wallet address
         * @param pins_name Name to resolve (e.g., "myname.pi")
         * @return Resolved wallet address, or empty if not found
         */
        std::optional<std::string> resolve(const std::string &pins_name);

        /**
         * Check if string is a valid PiNS name (not a raw address)
         * @param input String to check
         * @return true if it looks like a PiNS name, false if it's a raw address
         */
        static bool is_pins_name(const std::string &input);

        /**
         * Check if string is a valid wallet address
         * @param input String to check
         * @return true if it's a valid hex address
         */
        static bool is_wallet_address(const std::string &input);

        /**
         * Get cached resolution (without making API call)
         * @param pins_name Name to lookup
         * @return Cached address or empty if not cached
         */
        std::optional<std::string> get_cached(const std::string &pins_name) const;

    private:
        std::string node_url_;
        std::map<std::string, std::string> cache_; // pins_name -> address

        /**
         * Make HTTP GET request to node API
         * @param endpoint API endpoint (e.g., /api/v1/pins/resolve/myname)
         * @return Response body or empty string on error
         */
        std::string make_http_request(const std::string &endpoint);

        /**
         * Parse JSON response for wallet address
         * @param json_response JSON response from API
         * @return Extracted address or empty string
         */
        static std::string parse_address_from_json(const std::string &json_response);
    };

} // namespace psminer
