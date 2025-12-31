import requests
from bs4 import BeautifulSoup
import os
import shutil
import ipaddress

# 函数：从指定的ASN页面获取CIDR（支持缓存）
def get_cidrs(asn, cache_dir):
    # 定义缓存文件路径
    cache_file = os.path.join(cache_dir, f"{asn}_prefixes.html")
    
    # 如果缓存文件不存在，下载网页并保存
    if not os.path.exists(cache_file):
        print(f"正在下载并缓存ASN {asn} 的prefixes网页...")
        asn_url = f"https://bgp.he.net/{asn}#_prefixes"
        response = requests.get(asn_url)
        with open(cache_file, "w", encoding="utf-8") as file:
            file.write(response.text)
    else:
        print(f"使用缓存的ASN {asn} 的prefixes网页...")

    # 从缓存文件中读取内容
    with open(cache_file, "r", encoding="utf-8") as file:
        content = file.read()

    # 解析HTML，提取CIDR信息
    soup = BeautifulSoup(content, "html.parser")
    cidrs = []
    for row in soup.find_all('tr'):
        cidr = row.find('a')
        if cidr and '/net/' in cidr['href']:
            cidrs.append(cidr.text)

    return cidrs

# 函数：从搜索页面提取ASN编号
def get_asns(isp_name):
    search_url = f"https://bgp.he.net/search?search%5Bsearch%5D={isp_name}&commit=Search"
    response = requests.get(search_url)
    soup = BeautifulSoup(response.content, "html.parser")
    
    asns = []
    for row in soup.find_all('tr'):
        asn_link = row.find('a')
        if asn_link and 'AS' in asn_link.text:
            asns.append(asn_link.text)
    
    return asns

# 清空缓存目录
def clear_cache(cache_dir):
    if os.path.exists(cache_dir):
        print(f"清空缓存目录 {cache_dir}...")
        shutil.rmtree(cache_dir)
    os.makedirs(cache_dir)

# 合并和排序CIDR
def merge_and_sort_cidrs(cidrs):
    if not cidrs:
        return {'ipv4': [], 'ipv6': []}
    
    # 将CIDR字符串转换为网络对象
    networks = []
    for cidr in cidrs:
        try:
            if ':' in cidr:  # IPv6
                networks.append(ipaddress.IPv6Network(cidr, strict=False))
            else:  # IPv4
                networks.append(ipaddress.IPv4Network(cidr, strict=False))
        except ValueError as e:
            print(f"警告: 无法解析CIDR {cidr}: {e}")
            continue
    
    # 分别处理IPv4和IPv6
    ipv4_networks = [n for n in networks if isinstance(n, ipaddress.IPv4Network)]
    ipv6_networks = [n for n in networks if isinstance(n, ipaddress.IPv6Network)]
    
    # 分别排序IPv4和IPv6网络
    ipv4_networks.sort()
    ipv6_networks.sort()
    
    # 合并网络（保持地址覆盖等效）
    merged_ipv4 = list(ipaddress.collapse_addresses(ipv4_networks))
    merged_ipv6 = list(ipaddress.collapse_addresses(ipv6_networks))
    
    # 转换回字符串并返回
    return {
        'ipv4': [str(network) for network in merged_ipv4],
        'ipv6': [str(network) for network in merged_ipv6]
    }

# 函数：主流程，遍历ISP，获取ASN和CIDR并保存到两个txt文件
def main(isps, cache_dir, output_ipv4_file, output_ipv6_file):
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)

    # 使用集合来存储所有CIDR，避免重复
    ipv4_cidrs = set()
    ipv6_cidrs = set()
    
    for isp in isps:
        print(f"正在搜索ISP: {isp}")
        asns = get_asns(isp)
        for asn in asns:
            print(f"ASN: {asn}")
            cidrs = get_cidrs(asn, cache_dir)
            
            # 将CIDR添加到相应的集合中
            for cidr in cidrs:
                if ':' in cidr:  # 如果CIDR中有冒号，则是IPv6
                    ipv6_cidrs.add(cidr)
                else:  # 否则为IPv4
                    ipv4_cidrs.add(cidr)
                
            print(f"{len(cidrs)} 个CIDR已收集。")
        print("-" * 40)
    
    # 合并和排序CIDR
    print("正在合并和排序CIDR...")
    all_cidrs = list(ipv4_cidrs) + list(ipv6_cidrs)
    merged_results = merge_and_sort_cidrs(all_cidrs)
    
    # 保存到文件
    with open(output_ipv4_file, mode='w', encoding='utf-8') as ipv4_file:
        for cidr in merged_results['ipv4']:
            ipv4_file.write(f"{cidr}\n")
    
    with open(output_ipv6_file, mode='w', encoding='utf-8') as ipv6_file:
        for cidr in merged_results['ipv6']:
            ipv6_file.write(f"{cidr}\n")
    
    print(f"已合并并排序 {len(merged_results['ipv4'])} 个IPv4 CIDR，保存至 {output_ipv4_file}")
    print(f"已合并并排序 {len(merged_results['ipv6'])} 个IPv6 CIDR，保存至 {output_ipv6_file}")
    
    # 清空缓存
    clear_cache(cache_dir)

# 输入ISP列表、缓存目录和输出文件路径
isps_to_search = ["alibaba", "oracle", "it7"]  # 需要搜索的ISP
cache_dir = "cache"  # 缓存目录
output_ipv4_file = "VPS_CIDR_4.txt"  # 输出IPv4 CIDR的txt文件
output_ipv6_file = "VPS_CIDR_6.txt"  # 输出IPv6 CIDR的txt文件

if __name__ == "__main__":
    main(isps_to_search, cache_dir, output_ipv4_file, output_ipv6_file)
