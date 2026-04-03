import subprocess
import json
import os
from config import get_backend_path

class SubprocessManager:
    def __init__(self):
        self.exe_path = get_backend_path()
        
    def execute_backend(self, test_type: str, **kwargs) -> dict:

        if not os.path.exists(self.exe_path):
            return {"error": f"Backend executable not found at: {self.exe_path}"}
            
        cmd = [self.exe_path, "--test", test_type]
        
        if test_type == "cpu":
            if 'pi_digits' in kwargs:
                cmd.extend(["--pi_digits", str(kwargs['pi_digits'])])
            if 'matrix_size' in kwargs:
                cmd.extend(["--matrix_size", str(kwargs['matrix_size'])])

        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        try:
            proc = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                encoding='utf-8', 
                startupinfo=startupinfo, 
                check=True
            )
            
            output_str = proc.stdout.strip()
            if not output_str:
                return {"error": "Backend returned no output."}
                
            return json.loads(output_str)
            
        except subprocess.CalledProcessError as e:
            return {"error": f"Process Error (Exit Code {e.returncode}): {e.stderr}"}
        except json.JSONDecodeError:
            return {"error": f"Failed to decode JSON. Raw output: {proc.stdout[:100]}..."}
        except Exception as e:
            return {"error": str(e)}