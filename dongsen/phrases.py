"""多音字词组表。

字表 `zh_table.json` 每个字只存一个最常见读音，导致多音字读错：
  银行 → yín xíng（应为 yín háng）
  音乐 → yīn lè（应为 yīn yuè）

本表用「词组 → 读音序列」覆盖最常用的多音词。
匹配策略是**最长优先**：在文本当前位置尝试匹配最长的词条，
命中就用词条读音，否则回落到逐字查表。

数据格式：{"词": "音节1 音节2 ..."}，音节用数字标调（1-4，5=轻声）。
词表只收「逐字读音会错」的词，不是通用词典。
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# 多音字词组
# ---------------------------------------------------------------------------
# 按首字分组，便于按文本当前位置快速筛选
PHRASES: dict[str, list[tuple[str, list[str]]]] = {}


def _add(word: str, syllables: str) -> None:
    """注册一个词条。"""
    parts = syllables.split()
    if len(parts) != len(word):
        raise ValueError(f"词条长度不匹配: {word!r} vs {syllables!r}")
    PHRASES.setdefault(word[0], []).append((word, parts))


# --- 行 háng / xíng ---
_add("银行", "yin2 hang2")
_add("行业", "hang2 ye4")
_add("行列", "hang2 lie4")
_add("行情", "hang2 qing2")
_add("同行", "tong2 hang2")      # 同行业
_add("行家", "hang2 jia1")
_add("内行", "nei4 hang2")
_add("外行", "wai4 hang2")
_add("排行", "pai2 hang2")
_add("行当", "hang2 dang4")
_add("行距", "hang2 ju4")
_add("行会", "hang2 hui4")

# --- 乐 lè / yuè ---
_add("音乐", "yin1 yue4")
_add("乐器", "yue4 qi4")
_add("乐队", "yue4 dui4")
_add("乐谱", "yue4 pu3")
_add("乐曲", "yue4 qu3")
_add("乐团", "yue4 tuan2")
_add("乐章", "yue4 zhang1")
_add("乐理", "yue4 li3")
_add("声乐", "sheng1 yue4")
_add("器乐", "qi4 yue4")
_add("交响乐", "jiao1 xiang3 yue4")
_add("音乐会", "yin1 yue4 hui4")
_add("游乐场", "you2 le4 chang3")
_add("俱乐部", "ju4 le4 bu4")

# --- 重 zhòng / chóng ---
_add("重新", "chong2 xin1")
_add("重复", "chong2 fu4")
_add("重叠", "chong2 die2")
_add("重逢", "chong2 feng2")
_add("重申", "chong2 shen1")
_add("重建", "chong2 jian4")
_add("重来", "chong2 lai2")
_add("重返", "chong2 fan3")
_add("重修", "chong2 xiu1")
_add("重演", "chong2 yan3")
_add("重置", "chong2 zhi4")
_add("重启", "chong2 qi3")
_add("重读", "chong2 du2")
_add("重写", "chong2 xie3")
_add("重装", "chong2 zhuang1")
_add("重考", "chong2 kao3")
_add("重播", "chong2 bo1")

# --- 长 cháng / zhǎng ---
_add("长大", "zhang3 da4")
_add("成长", "cheng2 zhang3")
_add("生长", "sheng1 zhang3")
_add("增长", "zeng1 zhang3")
_add("队长", "dui4 zhang3")
_add("校长", "xiao4 zhang3")
_add("班长", "ban1 zhang3")
_add("家长", "jia1 zhang3")
_add("部长", "bu4 zhang3")
_add("首长", "shou3 zhang3")
_add("市长", "shi4 zhang3")
_add("县长", "xian4 zhang3")
_add("董事长", "dong3 shi4 zhang3")
_add("长辈", "zhang3 bei4")
_add("长老", "zhang3 lao3")
_add("长相", "zhang3 xiang4")
_add("长者", "zhang3 zhe3")
_add("长子", "zhang3 zi3")
_add("长孙", "zhang3 sun1")

# --- 了 le / liǎo ---
_add("了解", "liao3 jie3")
_add("了不起", "liao3 bu4 qi3")
_add("了如指掌", "liao3 ru2 zhi3 zhang3")
_add("没完没了", "mei2 wan2 mei2 liao3")
_add("受不了", "shou4 bu4 liao3")
_add("不得了", "bu4 de2 liao3")
_add("大不了", "da4 bu4 liao3")
_add("明了", "ming2 liao3")
_add("了结", "liao3 jie2")
_add("了断", "liao3 duan4")

# --- 着 zhe / zháo / zhuó ---
_add("着急", "zhao2 ji2")
_add("着火", "zhao2 huo3")
_add("着凉", "zhao2 liang2")
_add("睡着", "shui4 zhao2")
_add("着迷", "zhao2 mi2")
_add("着落", "zhuo2 luo4")
_add("着手", "zhuo2 shou3")
_add("着眼", "zhuo2 yan3")
_add("着重", "zhuo2 zhong4")
_add("着装", "zhuo2 zhuang1")
_add("沉着", "chen2 zhuo2")

# --- 得 dé / de / děi ---
_add("得到", "de2 dao4")
_add("得意", "de2 yi4")
_add("得意洋洋", "de2 yi4 yang2 yang2")
_add("得罪", "de2 zui4")
_add("难得", "nan2 de2")
_add("取得", "qu3 de2")
_add("获得", "huo4 de2")
_add("觉得", "jue2 de5")
_add("懂得", "dong3 de5")
_add("记得", "ji4 de5")
_add("晓得", "xiao3 de5")
_add("舍不得", "she3 bu5 de5")
_add("心得", "xin1 de2")
_add("得意门生", "de2 yi4 men2 sheng1")

# --- 为 wéi / wèi ---
_add("为了", "wei4 le5")
_add("因为", "yin1 wei4")
_add("为什么", "wei4 shen2 me5")
_add("成为", "cheng2 wei2")
_add("认为", "ren4 wei2")
_add("以为", "yi3 wei2")
_add("作为", "zuo4 wei2")
_add("行为", "xing2 wei2")
_add("为人", "wei2 ren2")
_add("为难", "wei2 nan2")
_add("为止", "wei2 zhi3")
_add("为何", "wei4 he2")
_add("为何如此", "wei4 he2 ru2 ci3")

# --- 和 hé / hè / huó / huò ---
_add("和平", "he2 ping2")
_add("和谐", "he2 xie2")
_add("温和", "wen1 he2")
_add("暖和", "nuan3 huo5")
_add("和面", "huo2 mian4")
_add("和稀泥", "huo4 xi1 ni2")
_add("附和", "fu4 he4")
_add("应和", "ying4 he4")

# --- 都 dōu / dū ---
_add("首都", "shou3 du1")
_add("都市", "du1 shi4")
_add("都城", "du1 cheng2")
_add("都会", "du1 hui4")
_add("成都", "cheng2 du1")

# --- 还 hái / huán ---
_add("还有", "hai2 you3")
_add("还是", "hai2 shi4")
_add("还要", "hai2 yao4")
_add("还是说", "hai2 shi4 shuo1")
_add("归还", "gui1 huan2")
_add("还钱", "huan2 qian2")
_add("还债", "huan2 zhai4")
_add("偿还", "chang2 huan2")
_add("退还", "tui4 huan2")

# --- 觉 jué / jiào ---
_add("感觉", "gan3 jue2")
_add("觉悟", "jue2 wu4")
_add("自觉", "zi4 jue2")
_add("睡觉", "shui4 jiao4")
_add("午觉", "wu3 jiao4")
_add("一觉", "yi1 jiao4")
_add("睡觉了", "shui4 jiao4 le5")

# --- 处 chǔ / chù ---
_add("处理", "chu3 li3")
_add("处于", "chu3 yu2")
_add("相处", "xiang1 chu3")
_add("处罚", "chu3 fa2")
_add("处置", "chu3 zhi4")
_add("处方", "chu3 fang1")
_add("到处", "dao4 chu4")
_add("好处", "hao3 chu5")
_add("坏处", "huai4 chu5")
_add("长处", "chang2 chu5")
_add("短处", "duan3 chu5")
_add("办事处", "ban4 shi4 chu4")
_add("售票处", "shou4 piao4 chu4")

# --- 差 chā / chà / chāi ---
_add("差别", "cha1 bie2")
_add("差异", "cha1 yi4")
_add("差距", "cha1 ju4")
_add("误差", "wu4 cha1")
_add("差不多", "cha4 bu5 duo1")
_add("差点", "cha4 dian3")
_add("出差", "chu1 chai1")
_add("差事", "chai1 shi4")

# --- 数 shù / shǔ ---
_add("数学", "shu4 xue2")
_add("数字", "shu4 zi4")
_add("数量", "shu4 liang4")
_add("数据", "shu4 ju4")
_add("数一数", "shu3 yi1 shu3")
_add("数不清", "shu3 bu4 qing1")
_add("数落", "shu3 luo5")

# --- 假 jiǎ / jià ---
_add("假如", "jia3 ru2")
_add("假设", "jia3 she4")
_add("虚假", "xu1 jia3")
_add("假话", "jia3 hua4")
_add("放假", "fang4 jia4")
_add("假期", "jia4 qi1")
_add("请假", "qing3 jia4")
_add("暑假", "shu3 jia4")
_add("寒假", "han2 jia4")
_add("假日", "jia4 ri4")

# --- 传 chuán / zhuàn ---
_add("传统", "chuan2 tong3")
_add("传说", "chuan2 shuo1")
_add("传播", "chuan2 bo1")
_add("传递", "chuan2 di4")
_add("传染", "chuan2 ran3")
_add("自传", "zi4 zhuan4")
_add("传记", "zhuan4 ji4")
_add("水浒传", "shui3 hu3 zhuan4")

# --- 尽 jìn / jǐn ---
_add("尽力", "jin4 li4")
_add("尽量", "jin3 liang4")
_add("尽快", "jin3 kuai4")
_add("尽管", "jin3 guan3")
_add("尽早", "jin3 zao3")
_add("尽可能", "jin3 ke3 neng2")
_add("尽头", "jin4 tou2")
_add("尽情", "jin4 qing2")

# --- 中 zhōng / zhòng ---
_add("中国", "zhong1 guo2")
_add("中间", "zhong1 jian1")
_add("中心", "zhong1 xin1")
_add("中午", "zhong1 wu3")
_add("中学", "zhong1 xue2")
_add("中奖", "zhong4 jiang3")
_add("中毒", "zhong4 du2")
_add("中暑", "zhong4 shu3")
_add("看中", "kan4 zhong4")
_add("命中", "ming4 zhong4")

# --- 空 kōng / kòng ---
_add("空气", "kong1 qi4")
_add("天空", "tian1 kong1")
_add("空间", "kong1 jian1")
_add("空调", "kong1 tiao2")
_add("空白", "kong4 bai2")
_add("空闲", "kong4 xian2")
_add("抽空", "chou1 kong4")
_add("有空", "you3 kong4")

# --- 干 gān / gàn ---
_add("干净", "gan1 jing4")
_add("干燥", "gan1 zao4")
_add("干杯", "gan1 bei1")
_add("饼干", "bing3 gan1")
_add("干部", "gan4 bu4")
_add("干活", "gan4 huo2")
_add("能干", "neng2 gan4")
_add("干嘛", "gan4 ma2")
_add("干什么", "gan4 shen2 me5")
_add("主干", "zhu3 gan4")

# --- 发 fā / fà ---
_add("发现", "fa1 xian4")
_add("发展", "fa1 zhan3")
_add("发生", "fa1 sheng1")
_add("发送", "fa1 song4")
_add("头发", "tou2 fa5")
_add("理发", "li3 fa4")
_add("发型", "fa4 xing2")
_add("白发", "bai2 fa4")

# --- 角 jiǎo / jué ---
_add("角度", "jiao3 du4")
_add("角落", "jiao3 luo4")
_add("三角形", "san1 jiao3 xing2")
_add("角色", "jue2 se4")
_add("主角", "zhu3 jue2")
_add("配角", "pei4 jue2")
_add("角逐", "jue2 zhu2")
_add("口角", "kou3 jiao3")

# --- 只 zhī / zhǐ ---
_add("只有", "zhi3 you3")
_add("只是", "zhi3 shi4")
_add("只能", "zhi3 neng2")
_add("只要", "zhi3 yao4")
_add("一只", "yi4 zhi1")
_add("两只", "liang3 zhi1")
_add("船只", "chuan2 zhi1")

# --- 藏 cáng / zàng ---
_add("收藏", "shou1 cang2")
_add("隐藏", "yin3 cang2")
_add("躲藏", "duo3 cang2")
_add("西藏", "xi1 zang4")
_add("宝藏", "bao3 zang4")
_add("藏族", "zang4 zu2")
_add("宝藏图", "bao3 zang4 tu2")

# --- 散 sàn / sǎn ---
_add("散步", "san4 bu4")
_add("散步去", "san4 bu4 qu4")
_add("散会", "san4 hui4")
_add("分散", "fen1 san4")
_add("散发", "san4 fa1")
_add("散文", "san3 wen2")
_add("散漫", "san3 man4")
_add("零散", "ling2 san3")

# --- 转 zhuǎn / zhuàn ---
_add("转身", "zhuan3 shen1")
_add("转变", "zhuan3 bian4")
_add("转换", "zhuan3 huan4")
_add("转发", "zhuan3 fa1")
_add("转让", "zhuan3 rang4")
_add("转圈", "zhuan4 quan1")
_add("转动", "zhuan4 dong4")
_add("旋转", "xuan2 zhuan3")
_add("转盘", "zhuan4 pan2")

# --- 调 tiáo / diào ---
_add("调整", "tiao2 zheng3")
_add("调节", "tiao2 jie2")
_add("调料", "tiao2 liao4")
_add("调皮", "tiao2 pi2")
_add("调查", "diao4 cha2")
_add("调换", "diao4 huan4")
_add("音调", "yin1 diao4")
_add("腔调", "qiang1 diao4")

# --- 便 biàn / pián ---
_add("方便", "fang1 bian4")
_add("便利", "bian4 li4")
_add("便当", "bian4 dang1")
_add("随便", "sui2 bian4")
_add("便宜", "pian2 yi5")
_add("占便宜", "zhan4 pian2 yi5")

# --- 血 xuè / xiě ---
_add("血液", "xue4 ye4")
_add("血管", "xue4 guan3")
_add("血型", "xue4 xing2")
_add("血压", "xue4 ya1")
_add("流血", "liu2 xue4")

# --- 落 luò / là ---
_add("落下", "luo4 xia4")
_add("落地", "luo4 di4")
_add("落实", "luo4 shi2")
_add("部落", "bu4 luo4")
_add("丢三落四", "diu1 san1 la4 si4")

# --- 骨 gǔ / gū ---
_add("骨头", "gu3 tou5")
_add("骨骼", "gu3 ge2")
_add("骨气", "gu3 qi4")
_add("骨碌", "gu1 lu5")

# --- 与 yǔ / yù ---
_add("与其", "yu3 qi2")
_add("参与", "can1 yu4")
_add("与会", "yu4 hui4")

# --- 薄 báo / bó ---
_add("薄片", "bao2 pian4")
_add("薄饼", "bao2 bing3")
_add("单薄", "dan1 bo2")
_add("薄弱", "bo2 ruo4")
_add("刻薄", "ke4 bo2")

# --- 强 qiáng / qiǎng / jiàng ---
_add("强大", "qiang2 da4")
_add("强调", "qiang2 diao4")
_add("坚强", "jian1 qiang2")
_add("勉强", "mian3 qiang3")
_add("强迫", "qiang3 po4")
_add("倔强", "jue4 jiang4")

# --- 系 xì / jì ---
_add("系统", "xi4 tong3")
_add("关系", "guan1 xi4")
_add("联系", "lian2 xi4")
_add("系列", "xi4 lie4")
_add("系鞋带", "ji4 xie2 dai4")

# --- 载 zài / zǎi ---
_add("装载", "zhuang1 zai4")
_add("载重", "zai4 zhong4")
_add("记载", "ji4 zai3")
_add("一年半载", "yi1 nian2 ban4 zai3")

# --- 分 fēn / fèn ---
_add("分钟", "fen1 zhong1")
_add("分开", "fen1 kai1")
_add("分析", "fen1 xi1")
_add("分享", "fen1 xiang3")
_add("分数", "fen1 shu4")
_add("部分", "bu4 fen5")
_add("成分", "cheng2 fen5")
_add("身份", "shen1 fen4")
_add("分外", "fen4 wai4")
_add("过分", "guo4 fen4")

# --- 冲 chōng / chòng ---
_add("冲锋", "chong1 feng1")
_add("冲洗", "chong1 xi3")
_add("冲动", "chong1 dong4")
_add("冲突", "chong1 tu1")
_add("冲劲", "chong4 jin4")
_add("冲床", "chong4 chuang2")

# --- 曲 qū / qǔ ---
_add("曲线", "qu1 xian4")
_add("弯曲", "wan1 qu1")
_add("曲折", "qu1 zhe2")
_add("歌曲", "ge1 qu3")
_add("戏曲", "xi4 qu3")
_add("曲调", "qu3 diao4")

# --- 奇 qí / jī ---
_add("奇怪", "qi2 guai4")
_add("奇迹", "qi2 ji4")
_add("好奇", "hao4 qi2")
_add("奇数", "ji1 shu4")
_add("奇偶", "ji1 ou3")

# --- 少 shǎo / shào ---
_add("多少", "duo1 shao5")
_add("少量", "shao3 liang4")
_add("少数", "shao3 shu4")
_add("减少", "jian3 shao3")
_add("少年", "shao4 nian2")
_add("少女", "shao4 nv3")
_add("少爷", "shao4 ye5")
_add("老少", "lao3 shao4")

# --- 量 liàng / liáng ---
_add("质量", "zhi4 liang4")
_add("能量", "neng2 liang4")
_add("力量", "li4 liang5")
_add("测量", "ce4 liang2")
_add("量体温", "liang2 ti3 wen1")
_add("打量", "da3 liang5")

# --- 结 jié / jiē ---
_add("结束", "jie2 shu4")
_add("结果", "jie2 guo3")
_add("结合", "jie2 he2")
_add("结论", "jie2 lun4")
_add("结实", "jie1 shi5")
_add("结巴", "jie1 ba5")
_add("结果子", "jie1 guo3 zi5")

# --- 铺 pū / pù ---
_add("铺路", "pu1 lu4")
_add("铺开", "pu1 kai1")
_add("铺张", "pu1 zhang1")
_add("店铺", "dian4 pu4")
_add("床铺", "chuang2 pu4")
_add("卧铺", "wo4 pu4")

# --- 弹 tán / dàn ---
_add("弹琴", "tan2 qin2")
_add("弹奏", "tan2 zou4")
_add("弹力", "tan2 li4")
_add("反弹", "fan3 tan2")
_add("子弹", "zi3 dan4")
_add("炸弹", "zha4 dan4")
_add("弹药", "dan4 yao4")

# --- 削 xuē / xiāo ---
_add("剥削", "bo1 xue1")
_add("削弱", "xue1 ruo4")
_add("削减", "xue1 jian3")
_add("削皮", "xiao1 pi2")
_add("削苹果", "xiao1 ping2 guo3")

# --- 磨 mó / mò ---
_add("磨练", "mo2 lian4")
_add("磨损", "mo2 sun3")
_add("折磨", "zhe2 mo2")
_add("磨坊", "mo4 fang2")
_add("磨面", "mo4 mian4")

# --- 露 lù / lòu ---
_add("露出", "lu4 chu1")
_add("露天", "lu4 tian1")
_add("暴露", "bao4 lu4")
_add("露面", "lou4 mian4")
_add("露馅", "lou4 xian4")

# --- 差遣类 ---
_add("差遣", "chai1 qian3")
_add("差旅", "chai1 lv3")

# --- 屏幕/刷 ---
_add("刷新", "shua1 xin1")
_add("刷牙", "shua1 ya2")
_add("刷子", "shua1 zi5")

# --- 数字类特殊 ---
_add("一个", "yi2 ge4")
_add("一样", "yi2 yang4")
_add("一起", "yi4 qi3")
_add("一定", "yi2 ding4")
_add("一般", "yi4 ban1")
_add("一些", "yi1 xie1")
_add("一边", "yi1 bian1")
_add("不是", "bu2 shi4")
_add("不要", "bu2 yao4")
_add("不能", "bu4 neng2")
_add("不会", "bu2 hui4")
_add("不同", "bu4 tong2")
_add("不错", "bu2 cuo4")


def normalize_phrases() -> None:
    """把词表按长度降序排列，保证最长优先匹配。"""
    for first in PHRASES:
        PHRASES[first].sort(key=lambda x: -len(x[0]))


normalize_phrases()


def match_phrase(text: str, pos: int) -> tuple[int, list[str]] | None:
    """在 text 的 pos 位置尝试匹配最长词条。

    返回 (匹配长度, 读音列表) 或 None。
    """
    if pos >= len(text):
        return None
    cands = PHRASES.get(text[pos])
    if not cands:
        return None
    for word, syllables in cands:
        if text.startswith(word, pos):
            return len(word), syllables
    return None


def stats() -> dict:
    """词表统计。"""
    total = sum(len(v) for v in PHRASES.values())
    return {
        "phrase_count": total,
        "first_chars": len(PHRASES),
        "longest": max((len(w) for v in PHRASES.values() for w, _ in v), default=0),
    }
