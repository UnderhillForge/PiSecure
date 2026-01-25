#include "smart_contract.hpp"
#include <iostream>
#include <fstream>
#include <sstream>
#include <regex>
#include <filesystem>

namespace fs = std::filesystem;

namespace pswallet
{

    // ScriptContext implementation
    ScriptContext::ScriptContext(const std::string &wallet_address,
                                 const std::string &contract_address)
        : wallet_address_(wallet_address), contract_address_(contract_address) {}

    void ScriptContext::register_function(const std::string &name,
                                          std::function<json(const json &)> func)
    {
        functions_[name] = func;
    }

    json ScriptContext::get_variable(const std::string &key) const
    {
        auto it = variables_.find(key);
        if (it != variables_.end())
        {
            return it->second;
        }
        return json();
    }

    void ScriptContext::set_variable(const std::string &key, const json &value)
    {
        variables_[key] = value;
    }

    // SmartContractEngine implementation

    json SmartContractEngine::execute_file(const std::string &script_file,
                                           const std::shared_ptr<ScriptContext> &context)
    {
        if (!fs::exists(script_file))
        {
            return {{"error", "Script file not found"}};
        }

        try
        {
            std::ifstream file(script_file);
            std::stringstream buffer;
            buffer << file.rdbuf();

            return execute(buffer.str(), context);
        }
        catch (const std::exception &e)
        {
            return {{"error", std::string("Failed to read script: ") + e.what()}};
        }
    }

    json SmartContractEngine::execute(const std::string &script_code,
                                      const std::shared_ptr<ScriptContext> &context)
    {
        // Validate script first
        std::string error = validate_script(script_code);
        if (!error.empty())
        {
            return {{"error", error}};
        }

        // Check sandbox constraints
        error = check_sandbox_constraints(script_code);
        if (!error.empty())
        {
            return {{"error", error}};
        }

        try
        {
            return execute_ast(script_code, context);
        }
        catch (const std::exception &e)
        {
            return {{"error", std::string("Execution error: ") + e.what()}};
        }
    }

    std::string SmartContractEngine::validate_script(const std::string &script_code)
    {
        // Basic syntax validation

        // Check for balanced braces
        int brace_count = 0;
        int paren_count = 0;
        int bracket_count = 0;

        bool in_string = false;
        bool in_comment = false;

        for (size_t i = 0; i < script_code.length(); ++i)
        {
            char c = script_code[i];
            char next = (i + 1 < script_code.length()) ? script_code[i + 1] : '\0';

            if (in_comment)
            {
                if (c == '\n')
                    in_comment = false;
                continue;
            }

            if (c == '/' && next == '/')
            {
                in_comment = true;
                continue;
            }

            if (c == '"' && (i == 0 || script_code[i - 1] != '\\'))
            {
                in_string = !in_string;
            }

            if (!in_string)
            {
                if (c == '{')
                    brace_count++;
                else if (c == '}')
                    brace_count--;
                else if (c == '(')
                    paren_count++;
                else if (c == ')')
                    paren_count--;
                else if (c == '[')
                    bracket_count++;
                else if (c == ']')
                    bracket_count--;
            }
        }

        if (brace_count != 0)
        {
            return "Unbalanced braces";
        }
        if (paren_count != 0)
        {
            return "Unbalanced parentheses";
        }
        if (bracket_count != 0)
        {
            return "Unbalanced brackets";
        }

        return "";
    }

    std::vector<std::string> SmartContractEngine::get_builtin_functions()
    {
        return {
            "transfer",      // Send tokens
            "get_balance",   // Query balance
            "get_time",      // Get current time
            "call_contract", // Call another contract
            "emit_event",    // Emit event
            "log",           // Logging
            "if",            // Conditional
            "while",         // Loop
            "require",       // Assertion
            "revert"         // Revert execution
        };
    }

    json SmartContractEngine::execute_ast(const std::string &script_code,
                                          const std::shared_ptr<ScriptContext> &context)
    {
        // Simple script parser - execute line by line

        json result;
        result["success"] = true;
        result["output"] = json::array();
        result["state"] = json::object();

        // Split into lines and process
        std::stringstream ss(script_code);
        std::string line;
        int line_num = 0;

        while (std::getline(ss, line))
        {
            line_num++;

            // Skip empty lines and comments
            if (line.empty() || line.find("//") == 0)
            {
                continue;
            }

            // Trim whitespace
            line.erase(0, line.find_first_not_of(" \t"));
            line.erase(line.find_last_not_of(" \t") + 1);

            // Check for transaction instruction
            if (line.find("transaction") == 0)
            {
                auto tx_result = execute_transaction(json::parse(line), context);
                result["output"].push_back(tx_result);
            }
            // Check for function call
            else if (line.find("call") == 0)
            {
                auto call_result = execute_call(json::parse(line), context);
                result["output"].push_back(call_result);
            }
            // Check for variable assignment
            else if (line.find("const") == 0 || line.find("let") == 0)
            {
                std::regex assign_regex("(const|let)\\s+(\\w+)\\s*=\\s*(.+)");
                std::smatch match;
                if (std::regex_search(line, match, assign_regex))
                {
                    std::string var_name = match[2];
                    std::string var_value = match[3];
                    context->set_variable(var_name, var_value);
                }
            }
        }

        // Store final context state
        result["state"] = context->get_state();

        return result;
    }

    json SmartContractEngine::execute_transaction(const json &instruction,
                                                  const std::shared_ptr<ScriptContext> &context)
    {
        // Execute a transaction instruction

        json result;
        result["type"] = "transaction";

        // Validate transaction fields
        if (!instruction.contains("to"))
        {
            result["error"] = "Missing 'to' field in transaction";
            return result;
        }
        if (!instruction.contains("amount"))
        {
            result["error"] = "Missing 'amount' field in transaction";
            return result;
        }

        result["success"] = true;
        result["to"] = instruction["to"];
        result["amount"] = instruction["amount"];
        result["memo"] = instruction.value("memo", "");
        result["tx_hash"] = ""; // Would be assigned by blockchain

        return result;
    }

    json SmartContractEngine::execute_call(const json &call_data,
                                           const std::shared_ptr<ScriptContext> &context)
    {
        // Execute a function call

        json result;

        if (!call_data.contains("function"))
        {
            result["error"] = "Missing 'function' in call";
            return result;
        }

        std::string func_name = call_data["function"];
        json params = call_data.value("params", json::object());

        // Check if function is registered
        const auto &functions = context->get_functions();
        if (functions.find(func_name) != functions.end())
        {
            try
            {
                result = functions.at(func_name)(params);
            }
            catch (const std::exception &e)
            {
                result["error"] = e.what();
            }
        }
        else
        {
            result["error"] = std::string("Unknown function: ") + func_name;
        }

        return result;
    }

    std::string SmartContractEngine::check_sandbox_constraints(const std::string &script_code)
    {
        // Prevent dangerous operations

        // Check for forbidden keywords
        std::vector<std::string> forbidden = {
            "exec",    // Shell execution
            "system",  // System calls
            "fork",    // Process forking
            "eval",    // Dynamic code evaluation
            "require", // File inclusion (controlled use)
            "unlink",  // File deletion
            "chmod"    // Permission changes
        };

        for (const auto &keyword : forbidden)
        {
            if (script_code.find(keyword) != std::string::npos)
            {
                // Check if it's in a comment
                std::regex comment_pattern("//.*" + keyword);
                if (std::regex_search(script_code, comment_pattern))
                {
                    continue; // OK in comment
                }

                return std::string("Forbidden operation: ") + keyword;
            }
        }

        // Check for excessive loops (prevent infinite loops)
        int while_count = 0;
        size_t pos = 0;
        while ((pos = script_code.find("while", pos)) != std::string::npos)
        {
            while_count++;
            pos += 5;
        }

        if (while_count > 10)
        {
            return "Too many loop constructs (max 10)";
        }

        // Check maximum script size (prevent DoS)
        if (script_code.length() > 1024 * 1024)
        { // 1MB max
            return "Script too large (max 1MB)";
        }

        return "";
    }

} // namespace pswallet
