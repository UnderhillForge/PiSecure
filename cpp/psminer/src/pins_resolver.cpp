// PiNS Resolver implementation
#include "pins_resolver.hpp"
#include <iostream>
#include <sstream>
#include <algorithm>
#include <cctype>
#include <cstdlib>

namespace psminer
{

    PiNSResolver::PiNSResolver(const std::string &node_url)
        : node_url_(node_url)
    {
        // Remove trailing slash if present
        if (!node_url_.empty() && node_url_.back() == '/')
        {
            node_url_.pop_back();
        }
    }

    bool PiNSResolver::is_pins_name(const std::string &input)
    {
        // PiNS names: alphanumeric + dots, no 0x prefix, typically end with .pi
        if (input.empty())
            return false;

        // Raw addresses start with 0x and are hex
        if (input.substr(0, 2) == "0x" || input.substr(0, 2) == "0X")
        {
            return false; // This is a raw address
        }

        // PiNS names are alphanumeric + dots/hyphens
        for (char c : input)
        {
            if (!std::isalnum(c) && c != '.' && c != '-')
            {
                return false; // Contains invalid character
            }
        }

        return true;
    }

    bool PiNSResolver::is_wallet_address(const std::string &input)
    {
        // Must start with 0x and be hex
        if (input.length() < 3 || input.substr(0, 2) != "0x")
        {
            return false;
        }

        // Check remaining characters are hex
        for (size_t i = 2; i < input.length(); ++i)
        {
            char c = input[i];
            if (!std::isxdigit(c))
            {
                return false;
            }
        }

        return true;
    }

    std::optional<std::string> PiNSResolver::get_cached(const std::string &pins_name) const
    {
        auto it = cache_.find(pins_name);
        if (it != cache_.end())
        {
            return it->second;
        }
        return std::nullopt;
    }

    std::optional<std::string> PiNSResolver::resolve(const std::string &pins_name)
    {
        // Check cache first
        auto cached = get_cached(pins_name);
        if (cached)
        {
            return cached;
        }

        // Make API request to resolve PiNS name
        std::string endpoint = "/api/v1/pins/resolve/" + pins_name;
        std::string response = make_http_request(endpoint);

        if (response.empty())
        {
            std::cerr << "Failed to resolve PiNS name: " << pins_name << std::endl;
            return std::nullopt;
        }

        // Parse address from JSON response
        std::string address = parse_address_from_json(response);

        if (address.empty())
        {
            std::cerr << "PiNS name not registered: " << pins_name << std::endl;
            return std::nullopt;
        }

        // Cache the result
        cache_[pins_name] = address;

        return address;
    }

    std::string PiNSResolver::make_http_request(const std::string &endpoint)
    {
        // Use curl command line tool for HTTP requests
        // This is a pragmatic approach that doesn't require libcurl as a library dependency
        std::string full_url = node_url_ + endpoint;

        // Escape shell special characters in URL
        std::string safe_url;
        for (char c : full_url)
        {
            if (c == ' ' || c == '&' || c == ';' || c == '|' || c == '<' || c == '>')
            {
                safe_url += '\\';
            }
            safe_url += c;
        }

        // Execute curl command and capture response
        std::string cmd = "curl -s --max-time 5 '" + full_url + "' 2>/dev/null";
        FILE *pipe = popen(cmd.c_str(), "r");
        if (!pipe)
        {
            std::cerr << "Failed to execute curl command" << std::endl;
            return "";
        }

        std::string result;
        char buffer[256];
        while (fgets(buffer, sizeof(buffer), pipe) != nullptr)
        {
            result += buffer;
        }
        pclose(pipe);

        return result;
    }

    std::string PiNSResolver::parse_address_from_json(const std::string &json_response)
    {
        // Simple JSON parsing for address field
        // Looking for: "address": "0x..." or "wallet_address": "0x..."

        std::string address_key = "\"address\":";
        size_t pos = json_response.find(address_key);

        if (pos == std::string::npos)
        {
            // Try alternative key
            address_key = "\"wallet_address\":";
            pos = json_response.find(address_key);
        }

        if (pos == std::string::npos)
        {
            return "";
        }

        // Move past the key and colon
        pos += address_key.length();

        // Skip whitespace
        while (pos < json_response.length() && std::isspace(json_response[pos]))
        {
            ++pos;
        }

        // Expect opening quote
        if (pos >= json_response.length() || json_response[pos] != '"')
        {
            return "";
        }
        ++pos;

        // Extract address until closing quote
        std::string address;
        while (pos < json_response.length() && json_response[pos] != '"')
        {
            address += json_response[pos];
            ++pos;
        }

        // Validate it looks like an address (starts with 0x)
        if (address.substr(0, 2) == "0x")
        {
            return address;
        }

        return "";
    }

} // namespace psminer
