import subprocess


if __name__ == "__main__":
    connected_wifi = get_current_connected_wifi()
    if connected_wifi:
        print(f"当前连接的WiFi密码: {connected_wifi['password']}")