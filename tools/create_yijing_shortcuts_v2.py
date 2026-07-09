import plistlib
import os
from collections import Counter

# 定义八卦和六十四卦的数据
# 格式: (is_hexagram, symbol, name_chinese, pinyin_full)
# is_hexagram: True for hexagrams, False for trigrams
# pinyin_full: for hexagrams, it's the full name pinyin with spaces (will be removed later by .replace(" ", ""))
#              for trigrams, it's just the trigram pinyin (no spaces needed)
YIJING_ENTRIES = [
    # 8 Trigrams
    (False, '☰', '乾', 'qian','1'), (False, '☷', '坤', 'kun','8'), (False, '☳', '震', 'zhen','2'),
    (False, '☴', '巽', 'xun','7'), (False, '☵', '坎', 'kan','6'), (False, '☲', '离', 'li','3'),
    (False, '☶', '艮', 'gen','5'), (False, '☱', '兑', 'dui','4'),

    # 64 Hexagrams (使用完整拼音，脚本会自动缩短)
    (True, '䷀', '乾为天', 'qian wei tian','tian'), (True, '䷁', '坤为地', 'kun wei di','di'),
    (True, '䷂', '水雷屯', 'shui lei zhun','zhun'), (True, '䷃', '山水蒙', 'shan shui meng','meng'),
    (True, '䷄', '水天需', 'shui tian xu','xu'), (True, '䷅', '天水讼', 'tian shui song','song'),
    (True, '䷆', '地水师', 'di shui shi','shi'), (True, '䷇', '水地比', 'shui di bi','bi'),
    (True, '䷈', '风天小畜', 'feng tian xiao chu','xiaochu'), (True, '䷉', '天泽履', 'tian ze lv','lv'),
    (True, '䷊', '地天泰', 'di tian tai','tai'), (True, '䷋', '天地否', 'tian di pi','pi'),
    (True, '䷌', '天火同人', 'tian huo tong ren','tongren'), (True, '䷍', '火天大有', 'huo tian da you','dayou'),
    (True, '䷎', '地山谦', 'di shan qian','qian'), (True, '䷏', '雷地豫', 'lei di yu','yu'),
    (True, '䷐', '泽雷随', 'ze lei sui','sui'), (True, '䷑', '山风蛊', 'shan feng gu','gu'),
    (True, '䷒', '地泽临', 'di ze lin','lin'), (True, '䷓', '风地观', 'feng di guan','guan'),
    (True, '䷔', '火雷噬嗑', 'huo lei shi he','shihe'), (True, '䷕', '山火贲', 'shan huo ben','ben'),
    (True, '䷖', '山地剥', 'shan di bo','bo'), (True, '䷗', '地雷复', 'di lei fu','fu'),
    (True, '䷘', '天雷无妄', 'tian lei wu wang','wuwang'), (True, '䷙', '山天大畜', 'shan tian da xu','daxu'),
    (True, '䷚', '山雷颐', 'shan lei yi','yi'), (True, '䷛', '泽风大过', 'ze feng da guo','daguo'),
    (True, '䷜', '坎为水', 'kan wei shui','shui'), (True, '䷝', '离为火', 'li wei huo','huo'),
    (True, '䷞', '泽山咸', 'ze shan xian','xian'), (True, '䷟', '雷风恒', 'lei feng heng','heng'),
    (True, '䷠', '天山遁', 'tian shan dun','dun'), (True, '䷡', '雷天大壮', 'lei tian da zhuang','dazhuang'),
    (True, '䷢', '火地晋', 'huo di jin','jin'), (True, '䷣', '地火明夷', 'di huo ming yi','mingyi'),
    (True, '䷤', '风火家人', 'feng huo jia ren','jiaren'), (True, '䷥', '火泽睽', 'huo ze kui','kui'),
    (True, '䷦', '水山蹇', 'shui shan jian','jian'), (True, '䷧', '雷水解', 'lei shui jie','jie'),
    (True, '䷨', '山泽损', 'shan ze sun','sun'), (True, '䷩', '风雷益', 'feng lei yi','yi'),
    (True, '䷪', '泽天夬', 'ze tian guai','guai'), (True, '䷫', '天风姤', 'tian feng gou','gou'),
    (True, '䷬', '泽地萃', 'ze di cui','cui'), (True, '䷭', '地风升', 'di feng sheng','sheng'),
    (True, '䷮', '泽水困', 'ze shui kun','kun'), (True, '䷯', '水风井', 'shui feng jing','jing'),
    (True, '䷰', '泽火革', 'ze huo ge','ge'), (True, '䷱', '火风鼎', 'huo feng ding','ding'),
    (True, '䷲', '震为雷', 'zhen wei lei','lei'), (True, '䷳', '艮为山', 'gen wei shan','shan'),
    (True, '䷴', '风山渐', 'feng shan jian','jian'), (True, '䷵', '雷泽归妹', 'lei ze gui mei','guimei'),
    (True, '䷶', '雷火丰', 'lei huo feng','fong'), (True, '䷷', '火山旅', 'huo shan lv','lv'),
    (True, '䷸', '巽为风', 'xun wei feng','feng'), (True, '䷹', '兑为泽', 'dui wei ze','ze'),
    (True, '䷺', '风水涣', 'feng shui huan','huan'), (True, '䷻', '水泽节', 'shui ze jie','jie'),
    (True, '䷼', '风泽中孚', 'feng ze zhong fu','zhongfu'), (True, '䷽', '雷山小过', 'lei shan xiao guo','xiaoguo'),
    (True, '䷾', '水火既济', 'shui huo ji ji','jiji'), (True, '䷿', '火水未济', 'huo shui wei ji','weiji')
]

def create_plist_file_custom_shortcuts():
    """
    Generates a .plist file for macOS text replacements with the latest shortcut scheme,
    including unique last pinyin parts.
    """
    # Use a dictionary to collect shortcuts and avoid duplicates for the same phrase (symbol)
    # Format: {shortcut: phrase_symbol}
    all_shortcuts_map = {}
    
    for is_hexagram, symbol, name_chinese, pinyin_full, simplize in YIJING_ENTRIES:
        if is_hexagram:
            pinyin_parts = pinyin_full.split(" ")
            shortcut_full = "".join(pinyin_parts)
            all_shortcuts_map[shortcut_full] = symbol
            #simple = "".join(simplize)
            #all_shortcuts_map[simple] = symbol

        else:
            # 八卦快捷键
            shortcut = f"edge({pinyin_full})"
            all_shortcuts_map[shortcut] = symbol
            #number = "".join(simplize)
            #all_shortcuts_map[number] = symbol

    # 将 map 转换为 plistlib 需要的列表格式
    replacements = [{'phrase': symbol, 'shortcut': shortcut} for shortcut, symbol in all_shortcuts_map.items()]

    plist_filename = "易经文本替换_v4.plist"
    
    with open(plist_filename, 'wb') as fp:
        plistlib.dump(replacements, fp)
        
    return plist_filename

if __name__ == '__main__':
    # 将工作目录切换到脚本所在的目录，以确保 .plist 文件在 tools 文件夹内生成
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    filename = create_plist_file_custom_shortcuts()
    print(f"✅ 成功生成了 '{filename}' 文件。")
    print(f"   文件位置: {os.path.join(os.getcwd(), filename)}")
    print("\n接下来，请按照以下步骤操作：")
    print("1. 打开“系统设置” > “键盘”。")
    print("2. 点击“文本替换...”按钮。")
    print(f"3. 将刚刚生成的 '{filename}' 文件直接拖拽到这个窗口中（建议先删除旧版本）。")
    print("4. 所有快捷键将自动导入。")