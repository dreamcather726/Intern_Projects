import subprocess
import platform

def get_wifi_info():
    """获取当前连接的WiFi信息和密码"""
    system = platform.system()
    
    if system == "Windows":
        # Windows系统
        try:
            # 获取当前连接的WiFi
            result = subprocess.check_output(
                ["netsh", "wlan", "show", "interfaces"],
                stderr=subprocess.STDOUT,
                text=True,
                encoding='gbk'
            )
            
            ssid = None
            for line in result.split('\n'):
                if "SSID" in line and "BSSID" not in line:
                    ssid = line.split(":")[1].strip()
                    break
            
            if not ssid:
                print("未连接WiFi")
                return None
            
            print(f"当前WiFi: {ssid}")
            
            # 获取WiFi密码
            try:
                password_result = subprocess.check_output(
                    ["netsh", "wlan", "show", "profile", ssid, "key=clear"],
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding='gbk'
                )
                
                for line in password_result.split('\n'):
                    if "关键内容" in line:
                        password = line.split(":")[1].strip()
                        print(f"WiFi密码: {password}")
                        return ssid, password
                
                print("无法获取密码（可能需要管理员权限）")
                return ssid, None
                
            except subprocess.CalledProcessError:
                print("无法获取密码（可能需要管理员权限）")
                return ssid, None
            
        except Exception as e:
            print(f"获取失败: {e}")
            return None, None
    
    elif system == "Linux":
        # Linux系统
        try:
            # 获取当前连接的WiFi
            result = subprocess.check_output(
                ["iwgetid", "-r"],
                stderr=subprocess.STDOUT,
                text=True
            ).strip()
            
            if not result:
                print("未连接WiFi")
                return None, None
            
            print(f"当前WiFi: {result}")
            
            # Linux系统获取密码比较复杂，需要root权限和配置文件访问
            print("Linux系统需要root权限才能获取WiFi密码")
            return result, None
                
        except Exception as e:
            print(f"获取失败: {e}")
            return None, None
    
    else:
        print(f"不支持的系统: {system}")
        return None, None

if __name__ == "__main__":
    ssid, password = get_wifi_info()
    if ssid:
        print("获取完成")
    else:
        print("获取失败")