import sqlite3
import os
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from collections import defaultdict
import config
import re

def is_path_excluded(file_path):
    for pattern in config.excluded_paths:
        if re.match(pattern, file_path):
            return True
    return False

def get_file_info(file_path):
    try:
        if not os.path.exists(file_path):
            return None
        
        stat = os.stat(file_path)
        return {
            'size': stat.st_size,
            'modified': stat.st_mtime
        }
    except Exception as e:
        print(f"获取文件信息失败 {file_path}: {e}")
        return None

def calculate_file_hash(file_path, db_size, db_modified, db_hash_data):
    try:
        if db_size == 0:
            return file_path, db_size, '', db_modified, True
        
        file_info = get_file_info(file_path)
        if file_info is None:
            return None
        
        actual_size = file_info['size']
        actual_modified = file_info['modified']
        
        if actual_size != db_size:
            print(f"文件大小不匹配 {file_path}: 数据库={db_size}, 实际={actual_size}")
            return None
        
        if db_hash_data is not None:
            hash_size = db_hash_data[0]
            hash_modified = db_hash_data[1]
            
            if actual_size == hash_size and abs(actual_modified - hash_modified) < 0.001:
                return file_path, actual_size, '', actual_modified, False
        
        hasher = hashlib.md5()
        with open(file_path, 'rb') as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        
        return file_path, actual_size, hasher.hexdigest(), actual_modified, True
    except Exception as e:
        print(f"计算哈希失败 {file_path}: {e}")
        return None

def process_disk_files(db_path, disk, files):
    conn = sqlite3.connect(db_path, timeout=30.0, isolation_level='DEFERRED')
    cursor = conn.cursor()
    
    file_dict = {file_path: (size, modified) for file_path, size, modified in files}
    file_paths = list(file_dict.keys())
    
    hash_data = {}
    batch_size = 500
    for i in range(0, len(file_paths), batch_size):
        batch = file_paths[i:i+batch_size]
        placeholders = ','.join(['?'] * len(batch))
        cursor.execute(f'SELECT Filepath, Size, Modified FROM Hash WHERE Filepath IN ({placeholders})', batch)
        for row in cursor.fetchall():
            hash_data[row[0]] = (row[1], row[2])
    
    processed = 0
    skipped = 0
    calculated = 0
    start_time = time.time()
    last_calc_time = time.time()
    
    for file_path in file_paths:
        try:
            result = calculate_file_hash(file_path, file_dict[file_path][0], file_dict[file_path][1], hash_data.get(file_path))
            if result:
                path, size, hash_val, modified_time, was_calculated = result
                
                if was_calculated:
                    cursor.execute('''
                    INSERT OR REPLACE INTO Hash (Filepath, Size, Hash, Modified)
                    VALUES (?, ?, ?, ?)
                    ''', (path, size, hash_val, modified_time))
                    conn.commit()
                    calculated += 1
                    
                    current_time = time.time()
                    elapsed_since_last = current_time - last_calc_time
                    if elapsed_since_last > 0:
                        current_speed = 1 / elapsed_since_last
                        total_to_process = len(file_paths) - skipped
                        print(f"计算哈希: [{calculated}/{total_to_process}] {path} ({current_speed:.1f} 文件/秒)")
                    last_calc_time = current_time
                else:
                    skipped += 1
                
                processed += 1
                    
        except Exception as e:
            print(f"处理文件 {file_path} 时出错: {e}")
    
    conn.close()
    
    elapsed = time.time() - start_time
    print(f"磁盘 {disk} 完成！共处理 {processed} 个文件，计算哈希: {calculated} 个，跳过: {skipped} 个，耗时 {elapsed:.2f} 秒")
    
    return processed, calculated, skipped

def populate_hash_table(db_path):
    conn = sqlite3.connect(db_path, timeout=30.0, isolation_level='DEFERRED')
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM duplicate')
    total_files = cursor.fetchone()[0]
    print(f"找到 {total_files} 个可能重复的文件")
    
    if total_files == 0:
        conn.close()
        return
    
    cursor.execute('SELECT Filepath, Size, Modified, Disk FROM duplicate')
    files = cursor.fetchall()
    
    conn.close()
    
    print(f"排除的路径规则:")
    for pattern in config.excluded_paths:
        print(f"  {pattern}")
    
    disk_files = defaultdict(list)
    excluded_count = 0
    for file_path, size, modified, disk in files:
        if is_path_excluded(file_path):
            excluded_count += 1
            continue
        disk_files[disk].append((file_path, size, modified))
    
    print(f"按磁盘分组:")
    for disk, disk_file_list in disk_files.items():
        print(f"  {disk}: {len(disk_file_list)} 个文件")
    
    if excluded_count > 0:
        print(f"已排除 {excluded_count} 个文件（匹配排除规则）")
    
    total_processed = 0
    total_calculated = 0
    total_skipped = 0
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=len(disk_files)) as executor:
        future_to_disk = {
            executor.submit(process_disk_files, db_path, disk, files): disk
            for disk, files in disk_files.items()
        }
        
        for future in as_completed(future_to_disk):
            disk = future_to_disk[future]
            try:
                processed, calculated, skipped = future.result()
                total_processed += processed
                total_calculated += calculated
                total_skipped += skipped
            except Exception as e:
                print(f"处理磁盘 {disk} 时出错: {e}")
    
    elapsed = time.time() - start_time
    print(f"\n所有磁盘处理完成！")
    print(f"总处理: {total_processed} 个文件")
    print(f"计算哈希: {total_calculated} 个文件")
    print(f"跳过: {total_skipped} 个文件")
    print(f"总耗时: {elapsed:.2f} 秒")
    if elapsed > 0:
        print(f"平均速度: {total_processed/elapsed:.1f} 文件/秒")

def show_statistics(db_path):
    conn = sqlite3.connect(db_path, timeout=30.0, isolation_level='DEFERRED')
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM Hash')
    total = cursor.fetchone()[0]
    print(f"\nHash表统计:")
    print(f"总记录数: {total}")
    
    cursor.execute('SELECT COUNT(DISTINCT Hash) FROM Hash WHERE Hash != ""')
    unique_hashes = cursor.fetchone()[0]
    print(f"唯一哈希值数: {unique_hashes}")
    
    cursor.execute('SELECT COUNT(*) FROM Hash WHERE Hash = ""')
    zero_size_files = cursor.fetchone()[0]
    print(f"零字节文件数: {zero_size_files}")
    
    cursor.execute('SELECT Hash, COUNT(*) as cnt FROM Hash WHERE Hash != "" GROUP BY Hash ORDER BY cnt DESC LIMIT 10')
    print(f"\n重复最多的哈希值:")
    for hash_val, count in cursor.fetchall():
        print(f"  {hash_val}: {count} 个文件")
    
    conn.close()

if __name__ == '__main__':
    db_path = 'file_index.db'
    
    print("开始计算文件哈希并填充Hash表...")
    populate_hash_table(db_path)
    
    print("\n显示统计信息...")
    show_statistics(db_path)