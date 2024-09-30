import os
import shutil
import zipfile
import requests
import ipaddress
import concurrent.futures
import multiprocessing

# 下载 zip 文件
url = "https://github.com/ipverse/asn-ip/archive/refs/heads/master.zip"
r = requests.get(url)
with open("master.zip", "wb") as code:
    code.write(r.content)

# 解压 zip 文件
with zipfile.ZipFile("master.zip", 'r') as zip_ref:
    zip_ref.extractall(".")

# 将 IPv4 和 IPv6 地址结果存储在两个列表中
ipv4_addresses = []
ipv6_addresses = []
included_asns = ['90', '792', '793', '794', '1215', '1216', '1217', '1218', '1219', '1630', '3457', '4184', '4191', '4192', '6142', '7160', '10884', '11049', '11479', '11506', '11625', '11887', '13832', '14506', '14544', '14919', '15135', '15179', '15519', '18837', '18916', '20037', '20054', '22435', '23885', '24185', '25820', '29976', '31898', '31925', '33517', '34135', '34947', '36282', '37963', '38538', '39467', '40921', '41900', '43894', '43898', '45102', '45103', '45104', '46403', '46558', '52019', '54253', '57748', '59028', '59051', '59052', '59053', '59054', '59055', '60285', '63295', '134963', '136025', '138207', '200705', '200981', '203267', '206209', '211914', '393218', '393314', '393676', '393773', '395010', '395738', '399966', '400981', '401341']

# 遍历 as 文件夹
for root, dirs, files in os.walk("asn-ip-master/as"):
    asn = root.split('/')[-1]  # 提取 ASN
    if asn in included_asns:
        # 处理 IPv4 地址
        if 'ipv4-aggregated.txt' in files:
            with open(os.path.join(root, 'ipv4-aggregated.txt'), 'r') as file:
                ipv4s = file.read().splitlines()
                for ip in ipv4s:
                    # 忽略包含井号的行
                    if not ip.startswith('#'):
                        ipv4_addresses.append(ip)
        
        # 处理 IPv6 地址
        if 'ipv6-aggregated.txt' in files:
            with open(os.path.join(root, 'ipv6-aggregated.txt'), 'r') as file:
                ipv6s = file.read().splitlines()
                for ip in ipv6s:
                    # 忽略包含井号的行
                    if not ip.startswith('#'):
                        ipv6_addresses.append(ip)

# 将字符串转换为 IPv4/IPv6 网络对象
ipv4_networks = [ipaddress.IPv4Network(ip, strict=False) for ip in ipv4_addresses]
ipv6_networks = [ipaddress.IPv6Network(ip, strict=False) for ip in ipv6_addresses]

# 合并并排序 CIDR 范围
def calculate_and_merge_networks(networks):
    ranges = [(int(net.network_address), int(net.broadcast_address)) for net in networks]
    ranges.sort()

    merged_ranges = []
    current_start, current_end = ranges[0]

    for start, end in ranges[1:]:
        if start <= current_end + 1:
            current_end = max(current_end, end)
        else:
            merged_ranges.append((current_start, current_end))
            current_start, current_end = start, end

    merged_ranges.append((current_start, current_end))

    merged_networks = []
    for start, end in merged_ranges:
        start_ip = ipaddress.ip_address(start)
        end_ip = ipaddress.ip_address(end)
        merged_networks.extend(ipaddress.summarize_address_range(start_ip, end_ip))

    return merged_networks

# 自动检测 CPU 核心数并设置线程数
def process_networks_in_parallel(networks):
    cpu_cores = multiprocessing.cpu_count()  # 自动获取CPU核心数
    thread_count = cpu_cores if cpu_cores > 1 else 1  # 至少1个线程
    chunk_size = max(1, len(networks) // thread_count)  # 每个线程处理的CIDR块大小
    network_chunks = [networks[i:i + chunk_size] for i in range(0, len(networks), chunk_size)]
    
    merged_results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=thread_count) as executor:
        future_to_chunk = {executor.submit(calculate_and_merge_networks, chunk): chunk for chunk in network_chunks}
        for future in concurrent.futures.as_completed(future_to_chunk):
            merged_results.extend(future.result())

    return calculate_and_merge_networks(merged_results)

# 并行处理 IPv4 和 IPv6
ipv4_merged_sorted = process_networks_in_parallel(ipv4_networks)
ipv6_merged_sorted = process_networks_in_parallel(ipv6_networks)

# 将合并并排序后的 IPv4 结果写入文件
with open('Clash/CloudflareCIDR.txt', 'w') as file:
    for ip in ipv4_merged_sorted:
        file.write(f"{ip}\n")

# 将合并并排序后的 IPv6 结果写入文件
with open('Clash/CloudflareCIDR-v6.txt', 'w') as file:
    for ip in ipv6_merged_sorted:
        file.write(f"{ip}\n")

# 清理下载的 zip 文件和解压的文件夹
os.remove("master.zip")
shutil.rmtree("asn-ip-master")