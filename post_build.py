import os
import sys
import shutil

def run_post_build():
    print("===================================================")
    print("Running Starlifter Post-Build Verification & Repair")
    print("===================================================")
    
    # 1. Resolve paths
    app_base = os.path.dirname(os.path.abspath(__file__))
    dist_internal = os.path.join(app_base, "dist", "Starlifter Requisition Terminal", "_internal")
    
    if not os.path.exists(dist_internal):
        print(f"Error: Compiled directory not found at: {dist_internal}")
        return
        
    # Get active system python directories
    sys_python_dir = os.path.dirname(sys.executable)
    print(f"Active Python interpreter: {sys.executable}")
    
    # Find site-packages
    site_packages = None
    for p in sys.path:
        if p.endswith("site-packages"):
            site_packages = p
            break
    if not site_packages:
        # Fallback search
        possible = os.path.join(sys_python_dir, "Lib", "site-packages")
        if os.path.exists(possible):
            site_packages = possible
            
    if not site_packages:
        print("Warning: Could not resolve site-packages path to check C-extensions.")
        return
        
    # 2. Repair NumPy C-extensions (.pyd files)
    sys_numpy = os.path.join(site_packages, "numpy")
    dest_numpy = os.path.join(dist_internal, "numpy")
    if os.path.exists(sys_numpy) and os.path.exists(dest_numpy):
        print("Checking NumPy C-extensions...")
        numpy_pyds = []
        for root, dirs, files in os.walk(sys_numpy):
            for f in files:
                if f.endswith(".pyd"):
                    numpy_pyds.append(os.path.join(root, f))
                    
        # Check if they exist in destination
        copied = 0
        for pyd in numpy_pyds:
            rel_path = os.path.relpath(pyd, sys_numpy)
            dest_file = os.path.join(dest_numpy, rel_path)
            if not os.path.exists(dest_file):
                os.makedirs(os.path.dirname(dest_file), exist_ok=True)
                shutil.copy(pyd, dest_file)
                copied += 1
        if copied > 0:
            print(f"-> Restored {copied} missing NumPy .pyd files")
        else:
            print("-> NumPy C-extensions are OK")

    # 3. Repair Pillow (PIL) C-extensions
    sys_pil = os.path.join(site_packages, "PIL")
    dest_pil = os.path.join(dist_internal, "PIL")
    if os.path.exists(sys_pil) and os.path.exists(dest_pil):
        print("Checking Pillow C-extensions...")
        pil_pyds = []
        for root, dirs, files in os.walk(sys_pil):
            for f in files:
                if f.endswith(".pyd"):
                    pil_pyds.append(os.path.join(root, f))
                    
        copied = 0
        for pyd in pil_pyds:
            rel_path = os.path.relpath(pyd, sys_pil)
            dest_file = os.path.join(dest_pil, rel_path)
            if not os.path.exists(dest_file):
                os.makedirs(os.path.dirname(dest_file), exist_ok=True)
                shutil.copy(pyd, dest_file)
                copied += 1
        if copied > 0:
            print(f"-> Restored {copied} missing Pillow .pyd files")
        else:
            print("-> Pillow C-extensions are OK")

    # 4. Sync correct Tcl/Tk DLLs
    print("Checking Tcl/Tk DLLs...")
    sys_dlls_dir = os.path.join(sys_python_dir, "DLLs")
    dlls = ["tcl86t.dll", "tk86t.dll"]
    if os.path.exists(sys_dlls_dir):
        for dll in dlls:
            src_dll = os.path.join(sys_dlls_dir, dll)
            if os.path.exists(src_dll):
                dest_dll = os.path.join(dist_internal, dll)
                shutil.copy(src_dll, dest_dll)
                print(f"-> Synchronized DLL: {dll}")

    # 5. Sync correct Tcl/Tk data scripts
    print("Checking Tcl/Tk data scripts...")
    sys_tcl_data = os.path.join(sys_python_dir, "tcl", "tcl8.6")
    sys_tk_data = os.path.join(sys_python_dir, "tcl", "tk8.6")
    
    if os.path.exists(sys_tcl_data):
        dest_tcl = os.path.join(dist_internal, "_tcl_data")
        if os.path.exists(dest_tcl):
            shutil.rmtree(dest_tcl)
        shutil.copytree(sys_tcl_data, dest_tcl)
        print("-> Synchronized _tcl_data folder")
        
    if os.path.exists(sys_tk_data):
        dest_tk = os.path.join(dist_internal, "_tk_data")
        if os.path.exists(dest_tk):
            shutil.rmtree(dest_tk)
        shutil.copytree(sys_tk_data, dest_tk)
        print("-> Synchronized _tk_data folder")
        
    print("===================================================")
    print("Verification completed successfully!")
    print("===================================================")

if __name__ == "__main__":
    run_post_build()
