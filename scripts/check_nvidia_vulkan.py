#!/usr/bin/env python3
"""Fail early when the container has CUDA but not a usable NVIDIA Vulkan ICD."""

from __future__ import annotations

import ctypes
import ctypes.util
import glob
import json
import os
import site
import sys
from pathlib import Path


class VkApplicationInfo(ctypes.Structure):
    _fields_ = [
        ("sType", ctypes.c_uint32),
        ("pNext", ctypes.c_void_p),
        ("pApplicationName", ctypes.c_char_p),
        ("applicationVersion", ctypes.c_uint32),
        ("pEngineName", ctypes.c_char_p),
        ("engineVersion", ctypes.c_uint32),
        ("apiVersion", ctypes.c_uint32),
    ]


class VkInstanceCreateInfo(ctypes.Structure):
    _fields_ = [
        ("sType", ctypes.c_uint32),
        ("pNext", ctypes.c_void_p),
        ("flags", ctypes.c_uint32),
        ("pApplicationInfo", ctypes.POINTER(VkApplicationInfo)),
        ("enabledLayerCount", ctypes.c_uint32),
        ("ppEnabledLayerNames", ctypes.POINTER(ctypes.c_char_p)),
        ("enabledExtensionCount", ctypes.c_uint32),
        ("ppEnabledExtensionNames", ctypes.POINTER(ctypes.c_char_p)),
    ]


def _find_vulkan_loader() -> str | None:
    # Isaac Sim ships a Vulkan loader used by Kit. Prefer testing that loader
    # when Isaac Sim is installed; the system loader remains a fallback for
    # lightweight diagnostics outside the Isaac Sim environment.
    patterns = (
        "isaacsim/extscache/omni.gpu_foundation-*/bin/deps/libvulkan.so.1",
        "isaacsim/extscache/omni.kit.xr.core-*/bin/libvulkan.so.1",
    )
    for package_dir in site.getsitepackages():
        for pattern in patterns:
            matches = sorted(glob.glob(str(Path(package_dir) / pattern)))
            if matches:
                return matches[0]
    return ctypes.util.find_library("vulkan")


def main() -> int:
    icd_path = Path(os.environ.get("VK_ICD_FILENAMES", "/etc/vulkan/icd.d/nvidia_icd.json"))
    if not icd_path.is_file():
        print(f"[vulkan-check] ICD manifest not found: {icd_path}", file=sys.stderr)
        return 2
    try:
        manifest = json.loads(icd_path.read_text())
        driver_library = manifest["ICD"]["library_path"]
        loader_path = _find_vulkan_loader()
        if not loader_path:
            raise FileNotFoundError(
                "Vulkan loader not found (install Vulkan loader or use the Isaac Sim environment)"
            )
        # Let the Vulkan loader discover exactly the NVIDIA ICD we inspected.
        os.environ["VK_ICD_FILENAMES"] = str(icd_path.resolve())
        loader = ctypes.CDLL(loader_path)
        create_instance = loader.vkCreateInstance
        create_instance.restype = ctypes.c_int32
        create_instance.argtypes = [
            ctypes.POINTER(VkInstanceCreateInfo),
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_void_p),
        ]
        app_info = VkApplicationInfo(
            0,
            None,
            b"sim-evals-vulkan-preflight",
            1,
            b"sim-evals",
            1,
            1 << 22,  # VK_API_VERSION_1_0
        )
        create_info = VkInstanceCreateInfo(
            1,
            None,
            0,
            ctypes.pointer(app_info),
            0,
            None,
            0,
            None,
        )
        instance = ctypes.c_void_p()
        result = create_instance(ctypes.byref(create_info), None, ctypes.byref(instance))
        if result != 0:
            result_name = {-9: "VK_ERROR_INCOMPATIBLE_DRIVER"}.get(
                result, "unknown Vulkan error"
            )
            raise RuntimeError(
                f"vkCreateInstance returned VkResult {result} ({result_name})"
            )
        destroy_instance = loader.vkDestroyInstance
        destroy_instance.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        destroy_instance(instance, None)
    except Exception as exc:  # pragma: no cover - diagnostic path
        capabilities = os.environ.get("NVIDIA_DRIVER_CAPABILITIES", "unset")
        print(
            f"[vulkan-check] NVIDIA Vulkan initialization failed for {icd_path}: {exc}. "
            f"NVIDIA_DRIVER_CAPABILITIES={capabilities}; verify the graphics driver "
            "libraries and ICD are present in the container (a shell-only variable "
            "change cannot mount driver libraries).",
            file=sys.stderr,
        )
        return 3
    print(
        f"[vulkan-check] vkCreateInstance succeeded with {loader_path}; "
        f"NVIDIA ICD {driver_library} selected from {icd_path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
