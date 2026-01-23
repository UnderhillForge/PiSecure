/**
 * pybind_sha256.cpp - Python bindings for validation SHA-256
 */
#include <pybind11/pybind11.h>
#include <pybind11/operators.h>
#include <pybind11/stl.h>
#include "../crypto/sha256.h"

namespace py = pybind11;
using namespace pisecure::crypto;

PYBIND11_MODULE(pisecure_cpp_crypto, m) {
    m.doc() = "PiSecure C++ crypto module (validation SHA-256, not mining)";
    
    py::class_<Sha256Ctx>(m, "Sha256Ctx")
        .def(py::init<>())
        .def("write", [](Sha256Ctx& self, py::bytes data) {
            const char* ptr = PyBytes_AsString(data.ptr());
            if (!ptr) throw std::runtime_error("Failed to read bytes");
            size_t len = PyBytes_Size(data.ptr());
            self.write(reinterpret_cast<const uint8_t*>(ptr), len);
            return std::ref(self);
        }, "Add data to hash")
        .def("finalize", [](Sha256Ctx& self) {
            uint8_t out[32];
            self.finalize(out);
            return py::bytes(reinterpret_cast<const char*>(out), 32);
        }, "Finalize and return 32-byte digest")
        .def("reset", [](Sha256Ctx& self) {
            return std::ref(self.reset());
        }, "Reset to initial state");
    
    m.def("sha256", [](py::bytes data) {
        const char* ptr = PyBytes_AsString(data.ptr());
        if (!ptr) throw std::runtime_error("Failed to read bytes");
        size_t len = PyBytes_Size(data.ptr());
        uint8_t out[32];
        sha256(reinterpret_cast<const uint8_t*>(ptr), len, out);
        return py::bytes(reinterpret_cast<const char*>(out), 32);
    }, "Single-shot SHA-256");
    
    m.def("sha256d", [](py::bytes data) {
        const char* ptr = PyBytes_AsString(data.ptr());
        if (!ptr) throw std::runtime_error("Failed to read bytes");
        size_t len = PyBytes_Size(data.ptr());
        uint8_t out[32];
        sha256d(reinterpret_cast<const uint8_t*>(ptr), len, out);
        return py::bytes(reinterpret_cast<const char*>(out), 32);
    }, "Single-shot double-SHA-256");
    
    m.def("sha256d64", [](py::bytes data, size_t blocks) {
        const char* ptr = PyBytes_AsString(data.ptr());
        if (!ptr) throw std::runtime_error("Failed to read bytes");
        size_t len = PyBytes_Size(data.ptr());
        if (len != blocks * 64) {
            throw std::runtime_error("Data length must be blocks * 64");
        }
        uint8_t* out = new uint8_t[blocks * 32];
        sha256d64(out, reinterpret_cast<const uint8_t*>(ptr), blocks);
        py::bytes result(reinterpret_cast<const char*>(out), blocks * 32);
        delete[] out;
        return result;
    }, "Batch double-SHA-256 (validation throughput)");
}
