#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ECDICT 修正版数据导出脚本
"""

import stardict
import json
import re
import os
import csv
from collections import defaultdict

while True:
    DB_NAME = input("请输入数据库名称: ")
    if DB_NAME:
        break

DB_NAME = DB_NAME.strip()

def british_to_american_phonetic(uk_phonetic):
    """英式音标转美式音标"""
    if not uk_phonetic:
        return ""
    
    us_phonetic = uk_phonetic
    us_phonetic = us_phonetic.replace('ɒ', 'ɑ')
    us_phonetic = us_phonetic.replace('ɑː', 'ɑ')
    us_phonetic = us_phonetic.replace('ɔː', 'ɔ')
    us_phonetic = us_phonetic.replace('ɪə', 'ɪr')
    us_phonetic = us_phonetic.replace('eə', 'ɛr')
    us_phonetic = us_phonetic.replace('ʊə', 'ʊr')
    us_phonetic = us_phonetic.replace('ɜː', 'ɝ')
    us_phonetic = us_phonetic.replace('uː', 'u')
    us_phonetic = us_phonetic.replace('iː', 'i')
    us_phonetic = re.sub(r'ə$', 'ər', us_phonetic)
    
    return us_phonetic

def detect_phonetic_system(phonetic):
    """检测音标体系"""
    if not phonetic:
        return 'unknown'
    
    british_features = ['ɒ', 'ɑː', 'ɪə', 'eə', 'ʊə', 'ɜː']
    american_features = ['ɑ', 'ər', 'ɔr', 'ɪr', 'ɛr', 'ɝ']
    
    british_count = sum(1 for feature in british_features if feature in phonetic)
    american_count = sum(1 for feature in american_features if feature in phonetic)
    
    if british_count > american_count:
        return 'british'
    elif american_count > british_count:
        return 'american'
    else:
        return 'neutral'

def is_valid_word(word):
    """判断是否为有效单词（排除特殊开头和数字开头）"""
    if not word:
        return False
    
    # 排除特殊开头和数字开头
    if word[0] in ['"', "'", '-', '.', '(', '（', "）", ")", "?", "_"] or word[0].isdigit():
        return False
    
    # 必须包含字母
    if not any(c.isalpha() for c in word):
        return False
    
    return True

def escape_sql_string(text):
    """转义SQL字符串，使用双引号包裹"""
    if text is None:
        return 'NULL'
    if isinstance(text, (int, float)):
        return str(text)
    
    text = str(text)
    # 转义双引号
    text = text.replace('"', '\\"')
    # 转义反斜杠
    # text = text.replace('\\', '\\\\')
    # 转义换行符
    text = text.replace('\n', '\\n')
    text = text.replace('\r', '\\r')
    text = text.replace('\t', '\\t')
    
    return f'"{text}"'

def escape_json_string(text):
    """对于JSON字段，不转义双引号"""
    if text is None:
        return 'NULL'
    if isinstance(text, (int, float)):
        return str(text)
    
    text = str(text)
    # 转义反斜杠
    text = text.replace('"', '\\"')
    
    return f'"{text}"'

def parse_exchange_field(exchange_str):
    """解析exchange字段，格式: p:loved/3:loves/d:loved/i:loving/s:loves"""
    if not exchange_str:
        return []
    
    exchanges = []
    parts = exchange_str.split('/')
    
    for part in parts:
        if ':' in part:
            pos_code, word = part.split(':', 1)
            exchanges.append((pos_code, word))
    
    return exchanges

def load_stardict_data():
    """加载stardict.csv数据"""
    print("=== 加载stardict.csv数据 ===")
    
    data = {}
    count = 0
    
    try:
        with open('data/stardict.csv', 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                word = row.get('word', '').strip()
                if word and is_valid_word(word):
                    data[word] = {
                        'phonetic': row.get('phonetic', ''),
                        'definition': row.get('definition', ''),
                        'translation': row.get('translation', ''),
                        'pos': row.get('pos', ''),
                        'collins': int(row.get('collins', 0) or 0),
                        'exchange': row.get('exchange', ''),
                        'audio': row.get('audio', '')
                    }
                    count += 1

                    if count % 100000 == 0:
                        print(f"已加载 {count} 个单词...")
    
    except Exception as e:
        print(f"加载stardict.csv失败: {e}")
        return {}
    
    print(f"加载完成: {len(data)} 个单词")
    return data

def export_word_dictionary(stardict_data):
    """导出单词词典"""
    print("\n=== 导出单词词典 ===")
    
    word_id_map = {}  # word -> id 映射
    
    with open('data/insert_word_dictionary.sql', 'w', encoding='utf-8') as f:
        f.write("-- 单词词典完整数据（修正版）\n")
        f.write(f"USE {DB_NAME};\n\n")
        
        count = 0
        batch_size = 1000
        values_list = []
        
        for word, data in stardict_data.items():
            if ' ' not in word: # 只要单词, 不要词组
                phonetic = data.get('phonetic', '') or ''
                system = detect_phonetic_system(phonetic)
                
                if system == 'british':
                    phonetic_uk = phonetic
                    phonetic_us = british_to_american_phonetic(phonetic)
                elif system == 'american':
                    phonetic_us = phonetic
                    phonetic_uk = phonetic
                else:
                    phonetic_uk = phonetic
                    phonetic_us = british_to_american_phonetic(phonetic)
                
                # 记录单词ID映射
                word_id = count + 1
                word_id_map[word] = word_id
                
                values = (
                    word_id,
                    escape_sql_string(word),
                    escape_sql_string(phonetic_uk),
                    escape_sql_string(phonetic_us),
                    escape_sql_string(data.get('definition', '')),
                    escape_sql_string(data.get('translation', '')),
                    escape_sql_string(data.get('pos', '')),  # pos_ratio字段
                    data.get('collins', 0),  # collins字段
                    escape_sql_string(data.get('audio', ''))
                )
                
                values_list.append(f"({', '.join(map(str, values))})")
                count += 1
                
                if count % batch_size == 0:
                    f.write("INSERT INTO word_dictionary (id, word, phonetic_uk, phonetic_us, translation_en, translation_zh, pos_ratio, collins, audio) VALUES\n")
                    f.write(',\n'.join(values_list))
                    f.write(';\n\n')
                    values_list = []

                if count > 0 and count % int(len(stardict_data) / 10) == 0:
                    print(f"已导出 {count} 个单词...")
        
        # 写入剩余数据
        if values_list:
            f.write("INSERT INTO word_dictionary (id, word, phonetic_uk, phonetic_us, translation_en, translation_zh, pos_ratio, collins, audio) VALUES\n")
            f.write(',\n'.join(values_list))
            f.write(';\n\n')
    
    print(f"单词词典导出完成: {count} 条")
    return count, word_id_map

def export_phrase_dictionary(stardict_data):
    """导出词组词典"""
    print("\n=== 导出词组词典 ===")
    
    count = 0
    batch_size = 1000
    values_list = []
    
    try:
        with open('data/insert_phrase_dictionary.sql', 'w', encoding='utf-8') as f:
            f.write("-- 词组词典完整数据（修正版）\n")
            f.write(f"USE {DB_NAME};\n\n")
            
            for word, data in stardict_data.items():
                if ' ' in word: # 只要词组, 不要单词
                    values = (
                        escape_sql_string(word),
                        escape_sql_string(data.get('definition', '')),
                        escape_sql_string(data.get('translation', '')),
                        escape_sql_string(data.get('audio', ''))
                    )
                    
                    values_list.append(f"({', '.join(map(str, values))})")
                    count += 1
                    
                    if count % batch_size == 0:
                        f.write("INSERT INTO phrase_dictionary (phrase, translation_en, translation_zh, audio) VALUES\n")
                        f.write(',\n'.join(values_list))
                        f.write(';\n\n')
                        values_list = []
                    
                    if count > 0 and len(stardict_data) > 10 and count % (len(stardict_data) / 10) == 0:
                        print(f"已导出 {count} 个词组...")
            
            if values_list:
                f.write("INSERT INTO phrase_dictionary (phrase, translation_en, translation_zh, audio) VALUES\n")
                f.write(',\n'.join(values_list))
                f.write(';\n\n')
    
    except Exception as e:
        print(f"导出词组失败: {e}")
    
    print(f"词组词典导出完成: {count} 条")
    return count

def export_word_lemma(stardict_data, word_id_map):
    """导出词形数据"""
    print("\n=== 导出词形数据 ===")
    
    with open('data/insert_word_lemma.sql', 'w', encoding='utf-8') as f:
        f.write("-- 词形变换完整数据（修正版）\n")
        f.write(f"USE {DB_NAME};\n\n")
        
        count = 0
        batch_size = 1000
        values_list = []
        
        for word, data in stardict_data.items():
            if word not in word_id_map:
                continue
                
            word_id = word_id_map[word]
            exchange_str = data.get('exchange', '')
            
            if exchange_str:
                exchanges = parse_exchange_field(exchange_str)
                
                for pos, variant_word in exchanges:
                    if is_valid_word(variant_word):
                        values = (
                            word_id,
                            escape_sql_string(pos),
                            escape_sql_string(variant_word)
                        )
                        
                        values_list.append(f"({', '.join(map(str, values))})")
                        count += 1
                        
                        if count % batch_size == 0:
                            f.write("INSERT INTO word_lemma (word_id, pos, word) VALUES\n")
                            f.write(',\n'.join(values_list))
                            f.write(';\n\n')
                            values_list = []

                        if count > 0 and len(exchanges) > 10 and count % int(len(exchanges) / 10) == 0:
                            print(f"已导出 {count} 条词形...")
        
        if values_list:
            f.write("INSERT INTO word_lemma (word_id, pos, word) VALUES\n")
            f.write(',\n'.join(values_list))
            f.write(';\n\n')
    
    print(f"词形数据导出完成: {count} 条")
    return count

def export_word_resemble(word_id_map):
    """导出近义词数据"""
    print("\n=== 导出近义词数据 ===")
    
    try:
        with open('resemble.txt', 'r', encoding='utf-8') as file:
            content = file.read()
        
        with open('data/insert_word_resemble.sql', 'w', encoding='utf-8') as f:
            f.write("-- 近义词完整数据（修正版）\n")
            f.write(f"USE {DB_NAME};\n\n")
            
            count = 0
            batch_size = 500
            values_list = []
            
            sections = content.split('\n\n')
            
            for section in sections:
                lines = section.strip().split('\n')
                if not lines:
                    continue
                
                words_line = None
                content_lines = []
                
                for line in lines:
                    line = line.strip()
                    if line.startswith('%'):
                        words_line = line[1:].strip()
                    elif line.startswith('-') and ':' in line:
                        content_lines.append(line)
                    elif line and not line.startswith('%'):
                        content_lines.append(line)
                
                if words_line and content_lines:
                    # 清理words字段，仅保留[a-z,]字符
                    clean_words = re.sub(r'[^a-z,]', '', words_line.lower())
                    
                    word_list = [w.strip() for w in clean_words.split(',') if w.strip()]
                    content = '\n'.join(content_lines)
                    
                    for word in word_list:
                        if word and len(word) > 1 and is_valid_word(word) and word in word_id_map:
                            word_id = word_id_map[word]
                            
                            values = (
                                escape_sql_string(clean_words),
                                word_id,
                                escape_sql_string(content)
                            )
                            
                            values_list.append(f"({', '.join(map(str, values))})")
                            count += 1
                            
                            if count % batch_size == 0:
                                f.write("INSERT INTO word_resemble (words, word_id, content) VALUES\n")
                                f.write(',\n'.join(values_list))
                                f.write(';\n\n')
                                values_list = []
                                print(f"已导出 {count} 条近义词...")
            
            if values_list:
                f.write("INSERT INTO word_resemble (words, word_id, content) VALUES\n")
                f.write(',\n'.join(values_list))
                f.write(';\n\n')
        
        print(f"近义词数据导出完成: {count} 条")
        return count
    
    except Exception as e:
        print(f"导出近义词数据失败: {e}")
        return 0

def export_word_roots():
    """导出词根数据"""
    print("\n=== 导出词根数据 ===")
    
    try:
        with open('wordroot.txt', 'r', encoding='utf-8') as file:
            content = file.read()
        
        data = json.loads(content)
        root_id_map = {}  # root -> id 映射
        
        with open('data/insert_word_roots.sql', 'w', encoding='utf-8') as f:
            f.write("-- 词根词缀完整数据（修正版）\n")
            f.write(f"USE {DB_NAME};\n\n")
            
            count = 0
            batch_size = 100
            values_list = []
            
            for root, info in data.items():
                if isinstance(info, dict):
                    # 检查词根是否有效（排除数字开头）
                    if not is_valid_word(root):
                        continue
                    
                    # 记录词根ID映射
                    root_id = count + 1
                    root_id_map[root] = root_id
                    
                    values = (
                        escape_json_string(root),  # 对JSON数据不转义双引号
                        escape_json_string(info.get('class', '')),
                        escape_json_string(info.get('origin', '')),
                        escape_json_string(info.get('meaning', '')),
                        escape_json_string(''),  # meaning_zh
                        escape_json_string(info.get('function', '')),
                        escape_json_string('')   # function_zh
                    )
                    
                    values_list.append(f"({', '.join(map(str, values))})")
                    count += 1
                    
                    if count % batch_size == 0:
                        f.write("INSERT INTO word_roots (`root`, `class`, `origin`, meaning_en, meaning_zh, function_en, function_zh) VALUES\n")
                        f.write(',\n'.join(values_list))
                        f.write(';\n\n')
                        values_list = []
            
            if values_list:
                f.write("INSERT INTO word_roots (`root`, `class`, `origin`, meaning_en, meaning_zh, function_en, function_zh) VALUES\n")
                f.write(',\n'.join(values_list))
                f.write(';\n\n')
        
        print(f"词根数据导出完成: {count} 条")
        return count, root_id_map
    
    except Exception as e:
        print(f"导出词根数据失败: {e}")
        return 0, {}

def export_word_root_example(root_id_map, word_id_map):
    """导出词根例词关系"""
    print("\n=== 导出词根例词关系 ===")
    
    try:
        with open('wordroot.txt', 'r', encoding='utf-8') as file:
            content = file.read()
        
        data = json.loads(content)
        
        with open('data/insert_word_root_example.sql', 'w', encoding='utf-8') as f:
            f.write("-- 词根例词关系完整数据（修正版）\n")
            f.write(f"USE {DB_NAME};\n\n")
            
            count = 0
            batch_size = 500
            values_list = []
            
            for root, info in data.items():
                if isinstance(info, dict) and root in root_id_map:
                    root_id = root_id_map[root]
                    
                    # 从example字段中提取例词
                    examples = info.get('example', [])
                    if isinstance(examples, list):
                        for example in examples:
                            if isinstance(example, str):
                                if example and is_valid_word(example) and example in word_id_map:
                                    word_id = word_id_map[example]
                                    
                                    values = (root_id, word_id)
                                    values_list.append(f"({', '.join(map(str, values))})")
                                    count += 1
                                    
                                    if count % batch_size == 0:
                                        f.write("INSERT INTO word_root_example (root_id, word_id) VALUES\n")
                                        f.write(',\n'.join(values_list))
                                        f.write(';\n\n')
                                        values_list = []
                                        print(f"已导出 {count} 条词根例词关系...")
            
            if values_list:
                f.write("INSERT INTO word_root_example (root_id, word_id) VALUES\n")
                f.write(',\n'.join(values_list))
                f.write(';\n\n')
        
        print(f"词根例词关系导出完成: {count} 条")
        return count
    
    except Exception as e:
        print(f"导出词根例词关系失败: {e}")
        return 0

def create_import_script():
    """创建导入脚本"""
    script_content = '''#!/bin/bash
# ECDICT 修正版完整数据导入脚本

echo "开始导入ECDICT修正版数据..."

DB_NAME="{DB_NAME}"
isReplaceDBName=false

read -p "当前数据库: $DB_NAME, 请输入新的数据库(回车保持不变): " db_name
if [ -n "$db_name" ]; then
    DB_NAME="$db_name"
    isReplaceDBName=true
fi
echo "数据库: $DB_NAME"

while true; do
    read -s -p "请输入mysql密码: " password
    echo  # 换行
    if [ -n "$password" ]; then
        break
    fi
done

# 检查MySQL是否可用
if ! command -v mysql &> /dev/null; then
    echo "错误: 未找到MySQL命令"
    exit 1
fi

process_file() {
    if [ "$isReplaceDBName" = false ]; then
        return
    fi

    local filename="$1"
    
    if [[ ! -f "$filename" ]]; then
        echo "错误: 文件 '$filename' 不存在"
        return 1
    fi
    
    echo "正在处理文件: $filename"
    # 在这里添加你的处理逻辑
    # 检测操作系统
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        sed -i '' -E "s/^USE [a-zA-Z_][a-zA-Z0-9_]*;/USE $DB_NAME;/" "$filename"
    else
        # Linux
        sed -i -E "s/^USE [a-zA-Z_][a-zA-Z0-9_]*;/USE $DB_NAME;/" "$filename"
    fi
    echo "文件处理完成"
}

# 1. 创建数据库和表
echo  # 换行
echo "1. 创建数据库表结构..."
process_file "create_final_schema.sql"
mysql -u root -p"$password" < create_final_schema.sql
if [ $? -ne 0 ]; then
    echo "错误: 创建表结构失败"
    exit 1
fi

# 2. 导入单词词典
echo  # 换行
echo "2. 导入单词词典..."
process_file "insert_word_dictionary.sql"
if ! mysql -u root -p"$password" < insert_word_dictionary.sql; then
    echo "错误: 导入单词词典失败"
    exit 1
fi

# 3. 导入词组词典
echo  # 换行
echo "3. 导入词组词典..."
process_file "insert_phrase_dictionary.sql"
if ! mysql -u root -p"$password" < insert_phrase_dictionary.sql; then
    echo "错误: 导入词组词典失败"
    exit 1
fi

# 4. 导入词根数据
echo  # 换行
echo "4. 导入词根数据..."
process_file "insert_word_roots.sql"
if ! mysql -u root -p"$password" < insert_word_roots.sql; then
    echo "错误: 导入词根数据失败"
    exit 1
fi

# 5. 导入词形数据
echo  # 换行
echo "5. 导入词形数据..."
process_file "insert_word_lemma.sql"
if ! mysql -u root -p"$password" < insert_word_lemma.sql; then
    echo "错误: 导入词形数据失败"
    exit 1
fi

# 6. 导入近义词数据
echo  # 换行
echo "6. 导入近义词数据..."
process_file "insert_word_resemble.sql"
if ! mysql -u root -p"$password" < insert_word_resemble.sql; then
    echo "错误: 导入近义词数据失败"
    exit 1
fi

# 7. 导入词根例词关系
echo  # 换行
echo "7. 导入词根例词关系..."
process_file "insert_word_root_example.sql"
if ! mysql -u root -p"$password" < insert_word_root_example.sql; then
    echo "错误: 导入词根例词关系失败"
    exit 1
fi

echo  # 换行
echo "数据导入完成！"
echo "数据统计："
mysql -u root -p"$password" -e "
USE $DB_NAME;
SELECT 'word_dictionary' as table_name, COUNT(*) as count FROM word_dictionary
UNION ALL
SELECT 'phrase_dictionary', COUNT(*) FROM phrase_dictionary
UNION ALL
SELECT 'word_lemma', COUNT(*) FROM word_lemma
UNION ALL
SELECT 'word_resemble', COUNT(*) FROM word_resemble
UNION ALL
SELECT 'word_roots', COUNT(*) FROM word_roots
UNION ALL
SELECT 'word_root_example', COUNT(*) FROM word_root_example;
"
'''
    
    with open('data/import_all_data.sh', 'w', encoding='utf-8') as f:
        f.write(script_content.replace('{DB_NAME}', DB_NAME))
    
    # 设置执行权限
    os.chmod('data/import_all_data.sh', 0o755)
    print("\n已创建导入脚本: data/import_all_data.sh")

def main():
    print("ECDICT 修正版数据导出")
    print("=" * 60+"\n")
    
    # 1. 加载stardict数据
    stardict_data = load_stardict_data()
    if not stardict_data:
        print("错误: 无法加载stardict数据")
        return
    
    # 2. 导出所有数据
    word_count, word_id_map = export_word_dictionary(stardict_data)
    phrase_count = export_phrase_dictionary(stardict_data)
    roots_count, root_id_map = export_word_roots()
    lemma_count = export_word_lemma(stardict_data, word_id_map)
    resemble_count = export_word_resemble(word_id_map)
    example_count = export_word_root_example(root_id_map, word_id_map)
    
    # 3. 创建导入脚本
    create_import_script()
    
    print("\n" + "=" * 60)
    print("修正版数据导出完成！")
    
    print(f"\n数据统计:")
    print(f"- 单词词典: {word_count:,} 条")
    print(f"- 词组词典: {phrase_count:,} 条")
    print(f"- 词形数据: {lemma_count:,} 条")
    print(f"- 近义词: {resemble_count:,} 条")
    print(f"- 词根词缀: {roots_count:,} 条")
    print(f"- 词根例词: {example_count:,} 条")
    print(f"- 总计: {word_count + phrase_count + lemma_count + resemble_count + roots_count + example_count:,} 条")
    
    print(f"\n生成的文件:")
    # print("- create_final_schema.sql (数据库表结构)")
    print("- insert_word_dictionary.sql (单词词典)")
    print("- insert_phrase_dictionary.sql (词组词典)")
    print("- insert_word_lemma.sql (词形数据)")
    print("- insert_word_resemble.sql (近义词数据)")
    print("- insert_word_roots.sql (词根数据)")
    print("- insert_word_root_example.sql (词根例词关系)")
    print("- import_all_data.sh (导入脚本)")

    print("\n运行导入: cd data && ./import_all_data.sh")

if __name__ == '__main__':
    main()
