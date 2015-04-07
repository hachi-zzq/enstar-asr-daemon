# -*- coding: utf-8 -*-
"""
测试返回给ipad端的句子对应关系算法
"""
import re
import math

"""
ASR报告转换器
"""
REPORT_TYPE_LESSON = 1
REPORT_TYPE_READ = 2

WORD_SEMANTIC_TYPE_NORMAL = 'NORMAL'
WORD_SEMANTIC_TYPE_SILENT = 'SILENT'
WORD_SEMANTIC_TYPE_SIGN = 'SIGN'

WORD_RECOGNITION_RESULT_CORRECT = 'CORRECT'
WORD_RECOGNITION_RESULT_SKIPPED = 'SKIPPED'
WORD_RECOGNITION_RESULT_INCORRECT = 'INCORRECT'
WORD_RECOGNITION_RESULT_REDUNDANT = 'REDUNDANT'

INTONATION_TYPE_RISE = 'RISE'
INTONATION_TYPE_FALL = 'FALL'
INTONATION_TYPE_FLAT = 'FLAT'
INTONATION_TYPE_UNAVAILABLE = 'UNAVAILABLE'

# 在ASR每个节点匹配原文的时候，过滤掉每个原文单词两边的标点符号
PUNCTUATION_CHARS = '\'",.?! ()*-—'
WORD_FILTER_CHARS = '.,!?{}<> ()*—'


def convert(report, sentence_map, report_type=REPORT_TYPE_LESSON):
    if report_type == 1:
        return _convert_lesson(report, sentence_map)
    else:
        return _convert_read(report, sentence_map)


def _convert_lesson(report, sentence_map):
    """
    转换报告成Enstar lesson的报告形式
    :param report:
    :param sentence_map:
    :return:
    """
    count_words = 0  # 统计单词数
    report['duration'] = 0
    is_available = True
    for s_index, asr_sentence in enumerate(report["lines"]):

        if asr_sentence['begin'] == asr_sentence['end']:
            is_available = is_available and False

        if report["lines"][s_index]['end'] != 0:
            report['duration'] = asr_sentence['end']

        sentence = sentence_map[s_index]
        sentence_id = sentence['id']
        text = sentence['text']
        # 替换花括号里的词组
        words = _raw_sentence2asr_sentence(text, sentence['asrText'], asr_sentence['words'])
        """
        搜索原文句子，把原文中的标点符号和不需要读的单词加到ASR 单词序列中
        """
        new_words, silent_index = _get_raw_words(text)

        """
        将新的ASR单词序列插入到报告中去
        """
        new_asr_words = []
        for index, new_word in enumerate(new_words):
            tmp_map = {'available': True}
            if len(words) > 0 and new_word.lower().strip(PUNCTUATION_CHARS) == words[0]['text'].lower():
                count_words += 1
                tmp_map = words[0]
                if words[0]['type'] != 2:  # 判断标准音单词是否正确
                    tmp_map['available'] = False
                else:
                    tmp_map['available'] = True
                max_volume_subword = reduce(lambda x, y: x if x['volume'] > y['volume'] else y, tmp_map['subwords'],
                                            {'volume': 0})
                tmp_map['volume'] = max_volume_subword['volume']  # 取出音素中最高音量
                tmp_map['semanticType'] = WORD_SEMANTIC_TYPE_NORMAL

                if 'score' in tmp_map:
                    del tmp_map['score']  # 原文报告不需要score
                del tmp_map['type']  # 原文报告不需要type
                del words[0]
            else:
                begin = 0
                if len(new_asr_words) > 0:
                    begin = new_asr_words[-1]["end"]
                tmp_map["text"] = new_word
                tmp_map["begin"] = begin
                tmp_map["end"] = begin
                tmp_map["volume"] = 0
                tmp_map['semanticType'] = WORD_SEMANTIC_TYPE_SIGN
                tmp_map['subwords'] = []

            char_star_index = len(''.join(new_words[:index]))
            char_end_index = char_star_index + len(new_word) - 1
            tmp_map['charBegin'] = char_star_index
            tmp_map['charEndBefore'] = char_end_index + 1
            if index in silent_index:  # 判断是否需要静音
                tmp_map['semanticType'] = WORD_SEMANTIC_TYPE_SILENT

            tmp_map['intonation'] = INTONATION_TYPE_UNAVAILABLE
            new_asr_words.append(tmp_map)
            if len(new_asr_words) > 2 and new_asr_words[-2]['semanticType'] != WORD_SEMANTIC_TYPE_NORMAL:
                new_asr_words[-2]['end'] = tmp_map['begin']

        report["lines"][s_index]['words'] = new_asr_words
        report["lines"][s_index]['id'] = sentence_id
        del report["lines"][s_index]['score']
        del report["lines"][s_index]['sample']
        del report["lines"][s_index]['usertext']

    report['sentences'] = report.pop('lines')
    """
    将统计信息写到报告中去
    """
    report['duration'] = report['duration']
    report["totalWords"] = count_words
    report['totalSentences'] = len(report["sentences"])
    report['speed'] = 0 if report['duration'] == 0 else round(report['totalWords'] * 1.0 / (report['duration'] / 60), 2)
    report['version'] = '1.0.1'

    return report, is_available


def _convert_read(report, sentence_map):
    """
    转换报告成Enstar read的报告形式
    :param report:
    :param sentence_map:
    :return:
    """
    count_words = 0  # 统计单词数
    count_user_words = 0  # 统计读的单词数
    count_user_sentences = 0  # 统计读的句子数
    report['duration'] = 0
    for s_index, asr_sentence in enumerate(report["lines"]):

        if report["lines"][s_index]['begin'] == report["lines"][s_index]['end']:
            report["lines"][s_index]['unread'] = True
        else:
            report["lines"][s_index]['unread'] = False
            count_user_sentences += 1
            report['duration'] = asr_sentence['end']

        sentence = sentence_map[s_index]
        sentence_id = sentence['id']
        text = sentence['text']
        # 替换花括号里的词组
        words = _raw_sentence2asr_sentence(text, sentence['asrText'], asr_sentence['words'])

        """
        搜索原文句子，把原文中的标点符号和不需要读的单词加到ASR 单词序列中
        """
        new_words, silent_index = _get_raw_words(text)

        """
        将新的ASR单词序列插入到报告中去
        """
        new_asr_words = []
        for index, new_word in enumerate(new_words):
            tmp_map = {}
            if len(words) > 0 and new_word.lower().strip(PUNCTUATION_CHARS) == words[0]['text'].lower():
                count_words += 1
                tmp_map = words[0]
                max_volume_subword = reduce(lambda x, y: x if x['volume'] > y['volume'] else y, tmp_map['subwords'],
                                            {'volume': 0})
                tmp_map['volume'] = max_volume_subword['volume']  # 取出音素中最高音量
                tmp_map['semanticType'] = WORD_SEMANTIC_TYPE_NORMAL
                if words[0]['type'] != 1 and words[0]['type'] != 4:  # 漏词和静音
                    count_user_words += 1

                del words[0]
            else:
                begin = 0
                if len(new_asr_words) > 0:
                    begin = new_asr_words[-1]["end"]
                tmp_map["text"] = new_word
                tmp_map["begin"] = begin
                tmp_map["end"] = begin
                tmp_map["volume"] = 0
                tmp_map["score"] = 0
                tmp_map['semanticType'] = WORD_SEMANTIC_TYPE_SIGN
                tmp_map['subwords'] = []
                tmp_map['type'] = 4  # 静音
                # 如果是多词，则把波形图附加到忽略词（空格，标点或者括号中去）
                added_words = []
                while len(words) > 0 and words[0]['type'] == 0:
                    tmp_map['subwords'].extend(words[0]['subwords'])
                    added_words.append(words[0]['text'])
                    count_user_words += 1
                    del words[0]

                if len(added_words) > 0:
                    # 把多出来的词附加到忽略词的前面
                    tmp_map['text'] = ' ' + ' '.join(added_words) + new_word
                    tmp_map['type'] = 0  # 多词

            tmp_map['recognitionResult'] = WORD_RECOGNITION_RESULT_INCORRECT
            if tmp_map['type'] == 0:  # 多词
                tmp_map['recognitionResult'] = WORD_RECOGNITION_RESULT_REDUNDANT
            if tmp_map['type'] == 1:  # 漏词
                tmp_map['recognitionResult'] = WORD_RECOGNITION_RESULT_SKIPPED
            if (tmp_map['type'] == 2 and tmp_map['score'] >= WORD_SCORE_MIN_THRESHOLD) or tmp_map[
                'type'] == 4:  # 正确词+标点+静音
                tmp_map['recognitionResult'] = WORD_RECOGNITION_RESULT_CORRECT
            if tmp_map['type'] == 3:  # 错词
                tmp_map['recognitionResult'] = WORD_RECOGNITION_RESULT_INCORRECT

            if index in silent_index:  # 判断是否需要静音
                tmp_map['semanticType'] = WORD_SEMANTIC_TYPE_SILENT

            del tmp_map['type']

            new_asr_words.append(tmp_map)
            if len(new_asr_words) > 2 and new_asr_words[-2]['semanticType'] != WORD_SEMANTIC_TYPE_NORMAL:
                new_asr_words[-2]['end'] = tmp_map['begin']

        report["lines"][s_index]['words'] = new_asr_words
        report["lines"][s_index]['id'] = sentence_id
        del report["lines"][s_index]['score']
        del report["lines"][s_index]['sample']
        del report["lines"][s_index]['usertext']

    report['sentences'] = report.pop('lines')
    """
    将统计信息写到报告中去
    """
    report["userTotalWords"] = count_user_words
    report['userTotalSentences'] = count_user_sentences
    report['speed'] = 0 if report['duration'] == 0 else round(
        report['userTotalWords'] * 1.0 / (report['duration'] / 60), 2)
    report['duration'] = report['duration']
    report["totalWords"] = count_words
    report['totalSentences'] = len(report["sentences"])
    report['version'] = '1.0.1'

    return report, True


"""
测试返回给ipad端的句子对应关系算法

1、完成度：读到的句子总数/课文句子数
2、发音：type=2 并且score大于阈值
        得分 = (正确词/读到的词)*完成度 * 100
3、语调：如果语素大于句子所有音素的平均频率一定的阈值，则认为是高音；低于平均频率某个阈值，则为低音。
        正确的词：学生读的语调的升降调趋势与标准音的升降调趋势一样
        得分 = (正确的词/读到的词数)*完成度 * 100
4、重音：如果语素大于句子所有音素的平均音量一定的阈值，则认为是重音。
        正确的词：学生读的重音趋势与标准音的重音趋势一样。
        正确的句子：所有的词都正确。
        得分 = (正确的词数/读到的词数)*完成度 * 100
5、流畅：如果词间距时间大于句子所有词间距时间的的平均值一定的阈值，则认为是停顿。如果词间距时间是0，则认为是连读。
        正确的词：学生读得词语之前的停顿和范文相应位置停顿一样。
        得分 = (正确的停顿词语/读到的总词数)*完成度 * 100
6、语速：先算出次数每分钟，每少读M个词扣1分，每多读N个词也扣1分
"""

# INTONATION_THRESHOLD = 0.50  # 大于等于平均值10%时候认为是高音
VOLUME_THRESHOLD = 0.30  # 大于等于平均值50%时候认为是重音
FLUENCY_THRESHOLD = 0.4

WORD_SCORE_MAX_THRESHOLD = 8.5  # 单词得分大于等于这个值的时候认为发音满分
WORD_SCORE_MIN_THRESHOLD = 3.5  # 单词得分大于等于这个值的时候认为发音正确

INTONATION_THRESHOLD = 0.99


def _get_score(_score):
    if _score >= WORD_SCORE_MAX_THRESHOLD:
        return 100
    if _score < WORD_SCORE_MIN_THRESHOLD:
        return 0
    return (_score - WORD_SCORE_MIN_THRESHOLD) / (WORD_SCORE_MAX_THRESHOLD - WORD_SCORE_MIN_THRESHOLD) * 100


def calculate(read, lesson):
    """
    计算得分，生成阅读报告
    :param read:处理过的ASR返回的阅读报告
    :param lesson:处理过的ASR返回的课文分析报告
    :return: 返回给计算好的报告
    """
    pronunciation_words = 0  # 发音的词数
    pronunciation_words_total_score = 0  # 发音正确的词总分数
    intonation_right = 0  # 音调正确的词数
    stress_right = 0  # 重音正确的词数
    total_fluency_right_count = 0  # 流畅度正确的单词间隔数目
    total_duration_count = 0
    for sentence_index, (read_sentence, lesson_sentence) in enumerate(zip(read['sentences'], lesson['sentences'])):
        if not read_sentence['unread']:
            read_volume_total = 0
            available_word_count = 0
            read_volume_word_count = 0
            lesson_volume_total = 0

            lesson_duration_total = 0
            read_duration_total = 0
            sentence_duration_count = 0

            for word_index, (read_word, lesson_word) in enumerate(
                    zip(read_sentence['words'], lesson_sentence['words'])):
                read_word['intonation'] = True
                read_word['stress'] = True
                read_word['pronunciation'] = True
                read_word['fluency'] = True

                for read_subword in read_word['subwords']:
                    del read_subword['subtext']  # 报告中删除subtext

                if lesson_word['semanticType'] == WORD_SEMANTIC_TYPE_NORMAL:
                    read_word['fluency'] = True if not 'fluency' in read_word else read_word['fluency']
                    read_word['pronunciation'] = True
                    if lesson_word['available']:
                        pronunciation_words += 1

                        if read_word['recognitionResult'] != WORD_RECOGNITION_RESULT_CORRECT:
                            read_word['pronunciation'] = False
                        else:
                            pronunciation_words_total_score += _get_score(read_word['score'])

                        if read_word['recognitionResult'] == WORD_RECOGNITION_RESULT_CORRECT or read_word[
                            'recognitionResult'] == WORD_RECOGNITION_RESULT_INCORRECT:
                            read_volume_word_count += 1
                            read_volume_total += read_word['volume']
                            if len(read_word['subwords']) == len(lesson_word['subwords']):
                                if _get_intonation_similarity(read_word['subwords'],lesson_word['subwords']) < INTONATION_THRESHOLD:
                                    read_word['intonation'] = False
                        else:
                            read_word['intonation'] = False

                        if read_word['intonation']:
                            intonation_right += 1

                        lesson_volume_total += lesson_word['volume']
                        available_word_count += 1


                else:  # 忽略不读的词或者停顿的词
                    if word_index != 0 and word_index != len(read_sentence['words']) - 1:
                        read_duration = read_word['end'] - read_word['begin']
                        lesson_duration = lesson_word['end'] - lesson_word['begin']
                        lesson_duration_total += lesson_duration
                        read_duration_total += read_duration
                        sentence_duration_count += 1

                del read_word['semanticType']  # 删除语义类型字段
                del read_word['score']

            total_duration_count += sentence_duration_count

            lesson_duration_ave = 0 if sentence_duration_count == 0 else lesson_duration_total / sentence_duration_count
            read_duration_ave = 0 if sentence_duration_count == 0 else read_duration_total / sentence_duration_count

            # 每个句子中所有单词的音量平均值
            read_volume_average = 0 if read_volume_word_count == 0 else read_volume_total / read_volume_word_count
            lesson_volume_average = 0 if available_word_count == 0 else lesson_volume_total / available_word_count

            for word_index, (read_word, lesson_word) in enumerate(
                    zip(read_sentence['words'], lesson_sentence['words'])):
                if lesson_word['available']:
                    if lesson_word['semanticType'] == WORD_SEMANTIC_TYPE_NORMAL:
                        read_word['stress'] = True
                        if (read_word['recognitionResult'] != WORD_RECOGNITION_RESULT_CORRECT and read_word[
                            'recognitionResult'] != WORD_RECOGNITION_RESULT_INCORRECT) or (
                                    (read_word['volume'] > read_volume_average * (1 + VOLUME_THRESHOLD)) ^ (
                                            lesson_word['volume'] > lesson_volume_average * (1 + VOLUME_THRESHOLD))):
                            read_word['stress'] = False
                        if read_word['stress']:
                            stress_right += 1
                    else:  # 忽略不读的词或者停顿的词
                        if word_index != 0 and word_index != len(read_sentence['words']) - 1:
                            read_duration = read_word['end'] - read_word['begin']
                            lesson_duration = lesson_word['end'] - lesson_word['begin']
                            if (((read_duration > (1 + FLUENCY_THRESHOLD) * read_duration_ave) and (
                                        lesson_duration > (1 + FLUENCY_THRESHOLD) * lesson_duration_ave)) or \
                                        ((1 - FLUENCY_THRESHOLD) * read_duration_ave <= read_duration <= (
                                                    1 + FLUENCY_THRESHOLD) * read_duration_ave and
                                                         (
                                                                     1 - FLUENCY_THRESHOLD) * lesson_duration_ave <= lesson_duration <= (
                                                         1 + FLUENCY_THRESHOLD) * lesson_duration_ave) or (
                                            read_duration == 0 and lesson_duration == 0)) and (
                                            read_sentence['words'][word_index + 1][
                                                'recognitionResult'] == WORD_RECOGNITION_RESULT_CORRECT or
                                            read_sentence['words'][word_index + 1][
                                                'recognitionResult'] == WORD_RECOGNITION_RESULT_INCORRECT):
                                read_sentence['words'][word_index + 1]['fluency'] = True
                                total_fluency_right_count += 1
                            else:
                                read_sentence['words'][word_index + 1]['fluency'] = False
        else:
            for word_index, read_word in enumerate(read_sentence['words']):
                read_word['intonation'] = False
                read_word['stress'] = False
                read_word['pronunciation'] = False
                read_word['fluency'] = False
                read_word['recognitionResult'] = WORD_RECOGNITION_RESULT_SKIPPED

                del read_word['semanticType']
                del read_word['score']

    read['pronunciationScore'] = 0 if pronunciation_words == 0 else round(
        pronunciation_words_total_score * 1.0 / pronunciation_words, 2)
    read['stressScore'] = 0 if pronunciation_words == 0 else round(stress_right * 1.0 / pronunciation_words * 100, 2)
    read['intonationScore'] = 0 if pronunciation_words == 0 else round(
        intonation_right * 1.0 / pronunciation_words * 100, 2)
    read['fluencyScore'] = 0 if total_duration_count == 0 else round(
        total_fluency_right_count * 1.0 / total_duration_count * 100, 2)

    completeness = read["userTotalSentences"] * 1.0 / read['totalSentences']
    read['finalScore'] = {
        "pronunciationScore": read['pronunciationScore'] * completeness,
        "intonationScore": read['intonationScore'] * completeness,
        "stressScore": read['stressScore'] * completeness,
        "fluencyScore": read['fluencyScore'] * completeness,
        "speedScore": 0,
        "overall": 0,
        "speedSituation": ""
    }
    return read


def _raw_sentence2asr_sentence(raw_sentence, asr_text, asr_words):
    """
    将ASR返回结果中属于同一个花括号中的单词合并起来.使用原文替换ASR句子中的花括号内容。
    例如：
    原文：I'm {21} years old.
    ASR句子：I'm {twent one} years old
    ASR返回结果节点：[{"test":"I'm"}, {"test":"twent"}, {"test":"one"}, {"test":"years"}, {"test":"old"}]
    经过处理，将ASR节点变为 [{"test":"I'm"}, {"test":"21"}, {"test":"years"}, {"test":"old"}]
    :param raw_sentence:
    :param asr_text:
    :param asr_words:
    :return:
    """
    asr_array = asr_text.split()
    # 拆分原文中花括号
    text_pattern = re.compile('\{.*?\}')
    replace_array = text_pattern.findall(raw_sentence)  # 原文的花括号

    '''
    寻找大括号中的单词在asr结果中的位置
    '''
    transferred_array = []
    i = 0
    asr_len = len(asr_array)
    while i < asr_len:
        if asr_array[i][0] == '{':
            tmp_start = i
            while i < asr_len and asr_array[i][-1] != '}':
                i += 1
            transferred_array.append((tmp_start, i))
        i += 1

    words = [w for w in asr_words if w['type'] != 4]
    '''
    合并花括号中的单词的时间和音素，并使用原文单词替换
    '''
    for transferred, replace in zip(transferred_array, replace_array):
        sub_words = []
        tmp_map = {
            "text": replace[1:-1],
            "begin": words[transferred[0]]['begin'],
            "end": words[transferred[1]]['end']
        }
        is_correct = True
        total_score = 0
        for index in range(transferred[0], transferred[1] + 1):
            sub_words.extend(words[index]['subwords'])
            is_correct = is_correct and words[index]['type'] == 2
            total_score += words[index]['score']
            words[index] = []

        tmp_map['score'] = total_score / (transferred[1] - transferred[0] + 1)

        if is_correct:
            tmp_map['type'] = 2
        else:
            tmp_map['type'] = 3

        tmp_map['subwords'] = sub_words
        words[transferred[0]] = tmp_map

    words = [w for w in words if len(w) > 0 and w['type'] != 4]  # ASR单词序列
    return words


def _get_raw_words(text):
    """
    搜索原文句子，把原文中的标点符号和不需要读的单词加到单词序列中
    :param text:
    :return:句子单词和标点序列；静音的索引序列
    """
    new_words = []
    j = 0
    text_len = len(text)
    silent_index = []
    while j < text_len:
        if text[j] == '<' and j + 1 < text_len and text[j + 1] == '<':  # 括号和里面不需要读的单词
            k1 = j
            while j < text_len and text[j] != '>' and j < text_len:
                j += 1
            j += 1
            if j < text_len and text[j] == '>':
                j += 1
                silent_index.append(len(new_words))  # 记录silent的词组位置
                new_words.append(text[k1: j].replace('<<', '').replace('>>', ''))
        elif text[j] == '{':  # 花括号和里面的单词
            k2 = j
            while j < text_len and text[j] != '}' and j < text_len:
                j += 1
            j += 1
            new_words.append(text[k2: j].replace('{', '').replace('}', ''))
        elif text[j] in PUNCTUATION_CHARS:  # 标点符号
            k3 = j
            while j < text_len and text[j] in PUNCTUATION_CHARS:
                j += 1
            new_words.append(text[k3: j])
        else:  # 单词
            k4 = j
            while j < text_len and text[j] not in WORD_FILTER_CHARS:  # 单词中可能含有单引号或者句号，单独处理
                j += 1
            while j - 1 > k4 and text[j - 1] == '\'':  # 如果单词最后是以单引号结尾则位置减一
                j -= 1
            new_words.append(text[k4: j])
    return new_words, silent_index


def _get_intonation_similarity(read_sub_words, lesson_sub_words):
    """
    使用余弦相似性判断两个单词所有语素的语调
    语调公式 T = 2595log(1+f/700)
    :param read_sub_words:
    :param lesson_sub_words:
    :return:
    """
    x, y, z = 0, 0, 0
    read_tone_arr = []
    lesson_tone_arr = []
    #tons_arr = []
    for read_sb_word, lesson_sub_word in zip(read_sub_words, lesson_sub_words):
        read_tone = read_sb_word['tone']
        lesson_tone = lesson_sub_word['tone']
        if lesson_tone[0] and lesson_tone[1] and lesson_tone[2] and read_tone[0] and read_tone[1] and read_tone[2]:
            read_tone_arr.extend(read_tone)
            lesson_tone_arr.extend(lesson_tone)
    if len(read_tone_arr) == 0:
        return 1
    read_tone_arr = map(lambda n: 0 if n == 0 else 2595 * math.log10(1 + n / 700.0), read_tone_arr)
    lesson_tone_arr = map(lambda n: 0 if n == 0 else 2595 * math.log10(1 + n / 700.0), lesson_tone_arr)
    # tons_arr.extend(read_tone_arr)
    # tons_arr.extend(lesson_tone_arr)
    # avg = sum(tons_arr) / len(tons_arr)
    # read_tone_arr = map(lambda n: n - avg, read_tone_arr)
    # lesson_tone_arr = map(lambda n: n - avg, lesson_tone_arr)
    for i in range(len(read_tone_arr)):
        x += read_tone_arr[i] * read_tone_arr[i]
        y += lesson_tone_arr[i] * lesson_tone_arr[i]
        z += read_tone_arr[i] * lesson_tone_arr[i]
    x = math.sqrt(x)
    y = math.sqrt(y)
    return z / (x * y)