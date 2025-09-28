-- ECDICT 最终数据库表结构
use english;

-- 1. 单词词典表
CREATE TABLE IF NOT EXISTS word_dictionary (
    id INT PRIMARY KEY AUTO_INCREMENT,
    word VARCHAR(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_as_cs UNIQUE NOT NULL COMMENT '单词',
    phonetic_uk VARCHAR(128) COMMENT '英音音标',
    phonetic_us VARCHAR(128) COMMENT '美音音标',
    translation_en TEXT COMMENT '英文译文',
    translation_zh TEXT COMMENT '中文译文',
    pos_ratio VARCHAR(255) COMMENT '词性及出现的比例',
    collins TINYINT DEFAULT 0 COMMENT '柯林斯星级',
    audio TEXT COMMENT '音频URL',
    
    INDEX idx_word (word),
    INDEX idx_collins (collins),
    FULLTEXT KEY ft_translation_en (translation_en),
    FULLTEXT KEY ft_translation_zh (translation_zh)
) ENGINE=InnoDB COMMENT='单词词典表';

-- 2. 单词变形表
CREATE TABLE IF NOT EXISTS word_lemma (
    id INT PRIMARY KEY AUTO_INCREMENT,
    word_id INT NOT NULL COMMENT '单词ID',
    pos VARCHAR(8) COMMENT '词性',
    word VARCHAR(128) NOT NULL COMMENT '变形词',
    
    INDEX idx_word_id (word_id),
    UNIQUE KEY uk_word_id_pos (word_id, pos),
    FOREIGN KEY (word_id) REFERENCES word_dictionary(id) ON DELETE CASCADE
) ENGINE=InnoDB COMMENT='单词变形表';

-- 3. 近义词表
CREATE TABLE IF NOT EXISTS word_resemble (
    id INT PRIMARY KEY AUTO_INCREMENT,
    words VARCHAR(255) NOT NULL COMMENT '近义词组',
    word_id INT NOT NULL COMMENT '单词ID',
    content TEXT COMMENT '辨析内容',
    
    INDEX idx_words (words),
    INDEX idx_word_id (word_id),
    FULLTEXT KEY ft_content (content),
    FOREIGN KEY (word_id) REFERENCES word_dictionary(id) ON DELETE CASCADE
) ENGINE=InnoDB COMMENT='近义词表';

-- 4. 词根词缀表
CREATE TABLE IF NOT EXISTS word_roots (
    id INT PRIMARY KEY AUTO_INCREMENT,
    root VARCHAR(64) NOT NULL UNIQUE COMMENT '词根词缀',
    class VARCHAR(128) COMMENT '类型',
    origin VARCHAR(64) COMMENT '来源',
    meaning_en TEXT COMMENT '英文意思',
    meaning_zh TEXT COMMENT '中文意思',
    function_en TEXT COMMENT '英文作用',
    function_zh TEXT COMMENT '中文作用',
    
    INDEX idx_root (root),
    INDEX idx_class (class),
    INDEX idx_origin (origin)
) ENGINE=InnoDB COMMENT='词根词缀表';

-- 5. 词组词典表
CREATE TABLE IF NOT EXISTS phrase_dictionary (
    id INT PRIMARY KEY AUTO_INCREMENT,
    phrase VARCHAR(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_as_cs NOT NULL UNIQUE COMMENT '词组',
    translation_en TEXT COMMENT '英文译文',
    translation_zh TEXT COMMENT '中文译文',
    audio TEXT COMMENT '音频URL',
    
    INDEX idx_phrase (phrase),
    FULLTEXT KEY ft_translation_en (translation_en),
    FULLTEXT KEY ft_translation_zh (translation_zh)
) ENGINE=InnoDB COMMENT='词组词典表';

-- 6. 词根例词表
CREATE TABLE IF NOT EXISTS word_root_example (
    id INT PRIMARY KEY AUTO_INCREMENT,
    root_id INT NOT NULL COMMENT '词根ID',
    word_id INT NOT NULL COMMENT '单词ID',
    
    INDEX idx_root_id (root_id),
    INDEX idx_word_id (word_id),
    UNIQUE KEY uk_root_word (root_id, word_id),
    FOREIGN KEY (root_id) REFERENCES word_roots(id) ON DELETE CASCADE,
    FOREIGN KEY (word_id) REFERENCES word_dictionary(id) ON DELETE CASCADE
) ENGINE=InnoDB COMMENT='词根例词表';
