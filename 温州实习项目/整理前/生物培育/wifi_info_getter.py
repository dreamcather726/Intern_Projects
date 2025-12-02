#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
树莓派WiFi信息获取工具
用于获取当前连接的WiFi名称和密码
"""

import os
import re
import subprocess
import platform
import json
import sys


def get_current_wifi_info():
    """
    获取当前连接的WiFi名称和密码
    
    Returns:
        tuple: (ssid, password) - WiFi名称和密码
    """
    try:
        system = platform.system()
        ssid = None
        password = "未找到密码"
        
        # 根据不同操作系统采用不同的获取方法
        if system == 'Linux':
            print("检测到Linux系统，正在获取WiFi信息...")
            # 获取当前连接的WiFi名称
            ssid = get_linux_ssid()
            
            if ssid:
                print(f"已找到WiFi名称: {ssid}")
                # 尝试多种方法获取密码
                password = get_linux_wifi_password(ssid)
            else:
                return None, "未连接到任何WiFi网络"
                
        elif system == 'Windows':
            print("检测到Windows系统，正在获取WiFi信息...")
            # Windows系统获取WiFi信息
            ssid, password = get_windows_wifi_info()
            
        else:
            print(f"警告: 当前系统 {system} 支持有限")
            return None, f"当前系统 {system} 支持有限"
        
        return ssid, password
        
    except Exception as e:
        print(f"获取WiFi信息时发生异常: {e}")
        return None, f"获取WiFi信息时出错: {e}"

def get_linux_ssid():
    """
    在Linux系统上获取当前连接的WiFi名称
    
    Returns:
        str: WiFi名称，如果未找到返回None
    """
    # 尝试多种命令获取SSID
    methods = [
        # 方法1: 使用iwgetid
        ['iwgetid', '-r'],
        # 方法2: 使用iw命令
        ['iw', 'dev'],
        # 方法3: 使用nmcli
        ['nmcli', '-t', '-f', 'active,ssid', 'dev', 'wifi'],
        # 方法4: 使用iwlist
        ['iwlist', 'scan'],
    ]
    
    for method in methods:
        try:
            result = subprocess.check_output(
                method,
                stderr=subprocess.DEVNULL,
                universal_newlines=True,
                encoding='utf-8',
                errors='replace'
            )
            
            # 根据不同命令解析输出
            if method[0] == 'iwgetid':
                ssid = result.strip()
                if ssid:
                    return ssid
            elif method[0] == 'iw':
                for line in result.split('\n'):
                    if 'ssid' in line:
                        parts = line.strip().split('ssid')
                        if len(parts) > 1:
                            ssid = parts[1].strip().strip('"')
                            if ssid:
                                return ssid
            elif method[0] == 'nmcli':
                for line in result.strip().split('\n'):
                    if line.startswith('yes:'):
                        ssid = line.split(':', 1)[1]
                        return ssid
            elif method[0] == 'iwlist':
                # 查找当前连接的网络（通常有'Quality'和'SSID'）
                in_network = False
                current_ssid = None
                for line in result.split('\n'):
                    if 'Cell' in line:
                        in_network = True
                        current_ssid = None
                    elif in_network and 'ESSID:' in line:
                        ssid_match = re.search(r'ESSID:"([^"]+)"', line)
                        if ssid_match:
                            current_ssid = ssid_match.group(1)
                    elif in_network and 'Quality=' in line and current_ssid:
                        # 假设信号质量最好的就是当前连接的
                        return current_ssid
        except Exception:
            # 如果方法失败，尝试下一个
            continue
    
    return None

def get_linux_wifi_password(ssid):
    """
    在Linux系统上获取指定WiFi的密码
    
    Args:
        ssid: WiFi名称
        
    Returns:
        str: WiFi密码或错误信息
    """
    password = "未找到密码"
    
    # 尝试多个可能的wpa_supplicant配置文件路径
    wpa_paths = [
        '/etc/wpa_supplicant/wpa_supplicant.conf',
        '/etc/wpa_supplicant.conf',
        '/var/run/wpa_supplicant/wpa_supplicant.conf',
        os.path.expanduser('~/.config/wpa_supplicant/wpa_supplicant.conf')
    ]
    
    # 方法1: 检查所有可能的wpa_supplicant配置文件
    for wpa_path in wpa_paths:
        if os.path.exists(wpa_path):
            try:
                content = None
                # 尝试直接读取
                try:
                    with open(wpa_path, 'r', encoding='utf-8', errors='replace') as f:
                        content = f.read()
                except PermissionError:
                    # 尝试使用sudo
                    try:
                        content = subprocess.check_output(
                            ['sudo', 'cat', wpa_path],
                            stderr=subprocess.DEVNULL,
                            universal_newlines=True,
                            encoding='utf-8',
                            errors='replace'
                        )
                    except Exception:
                        continue
                
                if content:
                    # 使用更宽松的正则表达式匹配SSID和密码
                    ssid_pattern = re.compile(r'network=\{[^\}]*ssid=["\']{}["\'][^\}]*\}'.format(re.escape(ssid)), re.DOTALL | re.IGNORECASE)
                    match = ssid_pattern.search(content)
                    
                    if match:
                        network_block = match.group(0)
                        # 尝试多种可能的psk格式
                        psk_patterns = [
                            r'psk=["\']([^"\']+)["\']',
                            r'psk=(\S+)'
                        ]
                        
                        for psk_pattern in psk_patterns:
                            psk_match = re.search(psk_pattern, network_block, re.IGNORECASE)
                            if psk_match:
                                password = psk_match.group(1)
                                print(f"从 {wpa_path} 找到密码")
                                return password
                        
                        # 检查是否是无密码网络
                        if 'key_mgmt=NONE' in network_block or 'key_mgmt=none' in network_block:
                            password = "无密码"
                            print(f"从 {wpa_path} 确定为无密码网络")
                            return password
            except Exception as e:
                print(f"读取 {wpa_path} 时出错: {e}")
    
    # 方法2: 使用nmcli获取密码
    try:
        # 先获取连接名称，因为连接名称可能与SSID不同
        con_name_result = subprocess.check_output(
            ['nmcli', '-t', '-f', 'name,ssid', 'connection', 'show'],
            stderr=subprocess.DEVNULL,
            universal_newlines=True,
            encoding='utf-8',
            errors='replace'
        )
        
        con_name = None
        for line in con_name_result.strip().split('\n'):
            if ':' in line:
                parts = line.split(':', 1)
                if len(parts) == 2 and parts[1] == ssid:
                    con_name = parts[0]
                    break
        
        # 如果找到了连接名称，尝试获取密码
        if con_name:
            password_result = subprocess.check_output(
                ['nmcli', '-s', '-g', '802-11-wireless-security.psk', 'connection', 'show', con_name],
                stderr=subprocess.DEVNULL,
                universal_newlines=True,
                encoding='utf-8',
                errors='replace'
            )
            
            password_result = password_result.strip()
            if password_result and password_result != '--':
                password = password_result
                print("从NetworkManager找到密码")
                return password
        
        # 直接尝试使用SSID作为连接名
        password_result = subprocess.check_output(
            ['nmcli', '-s', '-g', '802-11-wireless-security.psk', 'connection', 'show', f'"{ssid}"'],
            stderr=subprocess.DEVNULL,
            universal_newlines=True,
            encoding='utf-8',
            errors='replace'
        )
        
        password_result = password_result.strip()
        if password_result and password_result != '--':
            password = password_result
            print("从NetworkManager找到密码")
            return password
    except Exception:
        pass
    
    # 方法3: 尝试使用wpa_cli获取当前连接的配置
    try:
        # 获取当前连接的bssid
        bssid_result = subprocess.check_output(
            ['iwgetid', '-r', '-b'],
            stderr=subprocess.DEVNULL,
            universal_newlines=True,
            encoding='utf-8',
            errors='replace'
        ).strip()
        
        if bssid_result:
            # 获取接口名称
            iface_result = subprocess.check_output(
                ['iwgetid', '-r', '-i'],
                stderr=subprocess.DEVNULL,
                universal_newlines=True,
                encoding='utf-8',
                errors='replace'
            ).strip()
            
            if iface_result:
                # 使用wpa_cli获取网络信息
                wpa_cli_result = subprocess.check_output(
                    ['wpa_cli', '-i', iface_result, 'list_networks'],
                    stderr=subprocess.DEVNULL,
                    universal_newlines=True,
                    encoding='utf-8',
                    errors='replace'
                )
                
                # 解析输出查找匹配的网络ID
                for line in wpa_cli_result.strip().split('\n')[1:]:  # 跳过标题行
                    parts = line.split('\t')
                    if len(parts) >= 3 and parts[1] == ssid:
                        network_id = parts[0]
                        # 获取该网络的详细配置
                        network_info = subprocess.check_output(
                            ['wpa_cli', '-i', iface_result, 'get_network', network_id, 'psk'],
                            stderr=subprocess.DEVNULL,
                            universal_newlines=True,
                            encoding='utf-8',
                            errors='replace'
                        ).strip()
                        
                        if network_info and network_info != 'FAIL':
                            password = network_info
                            print("从wpa_cli找到密码")
                            return password
    except Exception:
        pass
    
    return password

def get_windows_wifi_info():
    """
    在Windows系统上获取当前连接的WiFi名称和密码
    
    Returns:
        tuple: (ssid, password) - WiFi名称和密码
    """
    try:
        # 获取当前连接的WiFi名称
        ssid_result = subprocess.check_output(
            ['netsh', 'wlan', 'show', 'interfaces'],
            universal_newlines=True,
            encoding='utf-8',
            errors='replace'
        )
        
        ssid_match = re.search(r'SSID\s+: ([^\r\n]+)', ssid_result)
        if not ssid_match:
            return None, "未连接到任何WiFi网络"
        
        ssid = ssid_match.group(1)
        
        # 获取WiFi密码
        password_result = subprocess.check_output(
            ['netsh', 'wlan', 'show', 'profile', ssid, 'key=clear'],
            universal_newlines=True,
            encoding='utf-8',
            errors='replace'
        )
        
        password_match = re.search(r'关键内容\s+: ([^\r\n]+)', password_result)
        if password_match:
            return ssid, password_match.group(1)
        else:
            # 检查是否是无密码网络
            if '身份验证         : 开放式' in password_result:
                return ssid, "无密码"
            return ssid, "未找到密码"
            
    except Exception as e:
        print(f"Windows系统获取WiFi信息出错: {e}")
        return None, f"获取WiFi信息时出错: {e}"


def get_wifi_info_json():
    """
    获取WiFi信息并返回JSON格式
    
    Returns:
        str: 包含WiFi信息的JSON字符串
    """
    ssid, password = get_current_wifi_info()
    
    wifi_info = {
        "event": "wifi_info",
        "ssid": ssid if ssid else "未连接",
        "password": password,
        "timestamp": subprocess.check_output(["date", "+%Y-%m-%d %H:%M:%S"], universal_newlines=True).strip()
    }
    
    return json.dumps(wifi_info, ensure_ascii=False, indent=2)


def main():
    """
    主函数，用于命令行调用
    """
    # 获取WiFi信息
    wifi_json = get_wifi_info_json()
    
    # 输出结果
    print(wifi_json)
    
    # 可选：将结果保存到文件
    if len(sys.argv) > 1 and sys.argv[1] == "--save":
        try:
            with open("wifi_info.json", "w", encoding="utf-8") as f:
                f.write(wifi_json)
            print("WiFi信息已保存到 wifi_info.json")
        except Exception as e:
            print(f"保存WiFi信息失败: {e}")


if __name__ == "__main__":
    main()