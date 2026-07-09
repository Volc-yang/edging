import plistlib
import os

# 定义八卦和六十四卦的数据
# 格式: (序号, 卦画, 卦名, 拼音)
YIJING_SYMBOLS = [
    # 8 Trigrams
    (0, '☰', '乾', 'qian'),
    (0, '☷', '坤', 'kun'),
    (0, '☳', '震', 'zhen'),
    (0, '☴', '巽', 'xun'),
    (0, '☵', '坎', 'kan'),
    (0, '☲', '离', 'li'),
    (0, '☶', '艮', 'gen'),
    (0, '☱', '兑', 'dui'),
    # 64 Hexagrams
    (1, '䷀', '乾为天', 'qian wei tian'),
    (2, '䷁', '坤为地', 'kun wei di'),
    (3, '䷂', '水雷屯', 'shui lei tun'),
    (4, '䷃', '山水蒙', 'shan shui meng'),
    (5, '䷄', '水天需', 'shui tian xu'),
    (6, '䷅', '天水讼', 'tian shui song'),
    (7, '䷆', '地水师', 'di shui shi'),
    (8, '䷇', '水地比', 'shui di bi'),
    (9, '䷈', '风天小畜', 'feng tian xiao xu'),
    (10, '䷉', '天泽履', 'tian ze lv'),
    (11, '䷊', '地天泰', 'di tian tai'),
    (12, '䷋', '天地否', 'tian di pi'),
    (13, '䷌', '天火同人', 'tian huo tong ren'),
    (14, '䷍', '火天大有', 'huo tian da you'),
    (15, '䷎', '地山谦', 'di shan qian'),
    (16, '䷏', '雷地豫', 'lei di yu'),
    (17, '䷐', '泽雷随', 'ze lei sui'),
    (18, '䷑', '山风蛊', 'shan feng gu'),
    (19, '䷒', '地泽临', 'di ze lin'),
    (20, '䷓', '风地观', 'feng di guan'),
    (21, '䷔', '火雷噬嗑', 'huo lei shi he'),
    (22, '䷕', '山火贲', 'shan huo ben'),
    (23, '䷖', '山地剥', 'shan di bo'),
    (24, '䷗', '地雷复', 'di lei fu'),
    (25, '䷘', '天雷无妄', 'tian lei wu wang'),
    (26, '䷙', '山天大畜', 'shan tian da chu'),
    (27, '䷚', '山雷颐', 'shan lei yi'),
    (28, '䷛', '泽风大过', 'ze feng da guo'),
    (29, '䷜', '坎为水', 'kan wei shui'),
    (30, '䷝', '离为火', 'li wei huo'),
    (31, '䷞', '泽山咸', 'ze shan xian'),
    (32, '䷟', '雷风恒', 'lei feng heng'),
    (33, '䷠', '天山遁', 'tian shan dun'),
    (34, '䷡', '雷天大壮', 'lei tian da zhuang'),
    (35, '䷢', '火地晋', 'huo di jin'),
    (36, '䷣', '地火明夷', 'di huo ming yi'),
    (37, '䷤', '风火家人', 'feng huo jia ren'),
    (38, '䷥', '火泽睽', 'huo ze kui'),
    (39, '䷦', '水山蹇', 'shui shan jian'),
    (40, '䷧', '雷水解', 'lei shui jie'),
    (41, '䷨', '山泽损', 'shan ze sun'),
    (42, '䷩', '风雷益', 'feng lei yi'),
    (43, '䷪', '泽天夬', 'ze tian guai'),
    (44, '䷫', '天风姤', 'tian feng gou'),
    (45, '䷬', '泽地萃', 'ze di cui'),
    (46, '䷭', '地风升', 'di feng sheng'),
    (47, '䷮', '泽水困', 'ze shui kun'),
    (48, '䷯', '水风井', 'shui feng jing'),
    (49, '䷰', '泽火革', 'ze huo ge'),
    (50, '䷱', '火风鼎', 'huo feng ding'),
    (51, '䷲', '震为雷', 'zhen wei lei'),
    (52, '䷳', '艮为山', 'gen wei shan'),
    (53, '䷴', '风山渐', 'feng shan jian'),
    (54, '䷵', '雷泽归妹', 'lei ze gui mei'),
    (55, '䷶', '雷火丰', 'lei huo feng'),
    (56, '䷷', '火山旅', 'huo shan lv'),
    (57, '䷸', '巽为风', 'xun wei feng'),
    (58, '䷹', '兑为泽', 'dui wei ze'),
    (59, '䷺', '风水涣', 'feng shui huan'),
    (60, '䷻', '水泽节', 'shui ze jie'),
    (61, '䷼', '风泽中孚', 'feng ze zhong fu'),
    (62, '䷽', '雷山小过', 'lei shan xiao guo'),
    (63, '䷾', '水火既济', 'shui huo ji ji'),
    (64, '䷿', '火水未济', 'huo shui wei ji')
]

def create_plist_file():
    """
    Generates a .plist file for macOS text replacements.
    """
    replacements = []
    
    # 使用 set 来确保快捷键的唯一性
    used_shortcuts = set()

    for number, symbol, name, pinyin in YIJING_SYMBOLS:
        # 基于拼音生成快捷键, e.g., (qian), (kun), (shui)
        # 如果是多音节，我们取第一个音节
        base_shortcut = pinyin.split(' ')[0]
        shortcut = f"({base_shortcut})"
        
        # 对于六十四卦，如果快捷键有重复，则附加上序号以保证唯一
        # 八卦的序号是0，六十四卦的序号是1-64
        if number > 0: # 64 Hexagrams
            temp_shortcut = shortcut
            count = 1
            while temp_shortcut in used_shortcuts:
                temp_shortcut = f"({base_shortcut}{count})"
                count += 1
            shortcut = temp_shortcut
        else: # 8 Trigrams
            # 对于八卦，如果快捷键重复，我们直接使用其拼音，并确保它在八卦之间是唯一的
            # 因为六十四卦的快捷键会带数字，所以八卦不带数字是唯一的
            pass # shortcut is already f"({base_shortcut})"


        replacements.append({'phrase': symbol, 'shortcut': shortcut})
        used_shortcuts.add(shortcut)

    # 定义输出文件名
    plist_filename = "易经文本替换.plist"
    
    # 写入 .plist 文件
    with open(plist_filename, 'wb') as fp:
        plistlib.dump(replacements, fp)
        
    return plist_filename

if __name__ == '__main__':
    filename = create_plist_file()
    print(f"✅ 成功生成了 '{filename}' 文件。")
    print("\n接下来，请按照以下步骤操作：")
    print("1. 打开“系统设置” > “键盘”。")
    print("2. 点击“文本替换...”按钮。")
    print(f"3. 将刚刚生成的 '{filename}' 文件直接拖拽到这个窗口中。")
    print("4. 所有快捷键将自动导入。")
