import requests
import geoip2.database
import ipaddress
import concurrent.futures
import os

def download_mmdb():
    url = "https://github.com/P3TERX/GeoLite.mmdb/raw/download/GeoLite2-ASN.mmdb"
    response = requests.get(url)
    with open("GeoLite2-ASN.mmdb", "wb") as f:
        f.write(response.content)
    print("GeoLite2-ASN.mmdb 下载完成")

def get_asn_cidrs(asn):
    cidrs_v4 = []
    cidrs_v6 = []
    with geoip2.database.Reader('GeoLite2-ASN.mmdb') as reader:
        for ip_network in [ipaddress.IPv4Network('0.0.0.0/0'), ipaddress.IPv6Network('::/0')]:
            for ip in ip_network:
                try:
                    response = reader.asn(ip)
                    if response.autonomous_system_number == asn:
                        network = ipaddress.ip_network(f"{ip}/128" if ip.version == 6 else f"{ip}/32")
                        if ip.version == 4:
                            cidrs_v4.append(network)
                        else:
                            cidrs_v6.append(network)
                except geoip2.errors.AddressNotFoundError:
                    pass
    
    return merge_cidrs(cidrs_v4), merge_cidrs(cidrs_v6)

def merge_cidrs(cidrs):
    merged = []
    for cidr in sorted(cidrs):
        if not merged or not merged[-1].supernet_of(cidr):
            merged.append(cidr)
        else:
            merged[-1] = merged[-1].supernet()
    return merged

def process_asn(asn):
    cidrs_v4, cidrs_v6 = get_asn_cidrs(int(asn))
    return asn, cidrs_v4, cidrs_v6

if __name__ == "__main__":
    download_mmdb()
    
    if not os.path.exists("GeoLite2-ASN.mmdb"):
        print("错误: GeoLite2-ASN.mmdb 文件不存在")
        exit(1)

    asn_list = ['90', '792', '793', '794', '1215', '1216', '1217', '1218', '1219', '1630', '3457', '4184', '4191', '4192', '6142', '7160', '10884', '11049', '11479', '11506', '11625', '11887', '13832', '14506', '14544', '14919', '15135', '15179', '15519', '18837', '18916', '20037', '20054', '22435', '23885', '24185', '25820', '29976', '31898', '31925', '33517', '34135', '34947', '36282', '37963', '38538', '39467', '40921', '41900', '43894', '43898', '45102', '45103', '45104', '46403', '46558', '52019', '54253', '57748', '59028', '59051', '59052', '59053', '59054', '59055', '60285', '63295', '134963', '136025', '138207', '200705', '200981', '203267', '206209', '211914', '393218', '393314', '393676', '393773', '395010', '395738', '399966', '400981', '401341']

    all_cidrs_v4 = []
    all_cidrs_v6 = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_to_asn = {executor.submit(process_asn, asn): asn for asn in asn_list}
        for future in concurrent.futures.as_completed(future_to_asn):
            asn, cidrs_v4, cidrs_v6 = future.result()
            all_cidrs_v4.extend(cidrs_v4)
            all_cidrs_v6.extend(cidrs_v6)
            print(f"已处理 ASN {asn}, 找到 {len(cidrs_v4)} 个 IPv4 CIDR 和 {len(cidrs_v6)} 个 IPv6 CIDR")

    merged_cidrs_v4 = merge_cidrs(all_cidrs_v4)
    merged_cidrs_v6 = merge_cidrs(all_cidrs_v6)

    with open('VPS_CIDR_4.txt', 'w') as f:
        for cidr in merged_cidrs_v4:
            f.write(f"{cidr}\n")

    with open('VPS_CIDR_6.txt', 'w') as f:
        for cidr in merged_cidrs_v6:
            f.write(f"{cidr}\n")

    print(f"IPv4 结果已保存到 VPS_CIDR_4.txt, 共 {len(merged_cidrs_v4)} 个 CIDR")
    print(f"IPv6 结果已保存到 VPS_CIDR_6.txt, 共 {len(merged_cidrs_v6)} 个 CIDR")
