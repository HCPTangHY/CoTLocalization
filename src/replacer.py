import ujson as json
import os,re
import shutil
import emoji

from .consts import *
from .log import logger

class Replacer:
    def __init__(self,version):
        self.version = version
        self.sourcePath = DIR_SOURCE/self.version
        self.fetchPath = DIR_FETCH/self.version
        self.transPath = DIR_TRANS/self.version
        self.translatedPath = DIR_TRANSLATED_SOURCE/self.version
        self.translation_files = {}
        pass
    def replace_file(self):
        if self.translatedPath.exists():
            shutil.rmtree(self.translatedPath)
        os.makedirs(self.translatedPath/"Passages", exist_ok=True)
        for root, dirs, files in os.walk(self.transPath):
            for d in dirs:
                if not os.path.exists(self.translatedPath/d):
                    os.makedirs(self.translatedPath/d)
            for file in files:
                with open(f"{root}\\{file}", "r", encoding="utf-8") as fp:
                    pzdata = json.load(fp)
                with open(f"{root.replace('trans','fetch')}\\{file}", "r", encoding="utf-8") as fp:
                    fetch_data = json.load(fp)
                if "Passage" in root:
                    with open(f"{root.replace('trans','marge_source')}\\{file.replace('.json','.twee')}","r",encoding="utf-8-sig") as fp:
                        file_content = fp.read()
                elif "Widget" in root:
                    with open(f"{root.replace('trans','source')}\\{file.replace('.json','.twee')}","r",encoding="utf-8-sig") as fp:
                        file_content = fp.read()
                elif "js"==root[-2]+root[-1]:
                    with open(f"{root.replace('trans','source')}\\{file.replace('.json','.js')}","r",encoding="utf-8-sig") as fp:
                        file_content = fp.read()
                else:
                    logger.error(f"no file {root}\{file}!")
                logger.info(f"file {file} readed")
                idx = 1
                delta_index = 0
                target_file_parts = []
                last_idx = 0

                # 基于 context 内的 <<POS:...>> 获取位置（JS为文件绝对位置；Twee为段落正文内相对位置）
                is_js_file = ("js" == root[-2]+root[-1])
                passage_body_start_cache = {}

                def extract_pos_from_context(ctx: str):
                    if not ctx:
                        return None
                    matches = re.findall(r'<<POS:(\d+)>>', ctx)
                    return int(matches[-1]) if matches else None

                def get_passage_name_from_key(key: str):
                    # Twee 的 key 形如 "{PassageName}_{fingerprint}"；PassageName 本身可能含有下划线
                    if "_" in key:
                        return key.rsplit("_", 1)[0]
                    return key

                def find_passage_body_start(passage_name: str):
                    if not passage_name:
                        return 0
                    if passage_name in passage_body_start_cache:
                        return passage_body_start_cache[passage_name]
                    if passage_name == "Global":
                        passage_body_start_cache[passage_name] = 0
                        return 0
                    # 在源码中查找段落标题行，计算正文起点（换行后第一个字符）
                    pattern = re.compile(rf'(?m)^::[ \t]{re.escape(passage_name)}[ \t]*\r?\n')
                    m = pattern.search(file_content)
                    if m:
                        start = m.end()
                        passage_body_start_cache[passage_name] = start
                        return start
                    # 兆底：朴素查找
                    idx_name = file_content.find(f":: {passage_name}")
                    if idx_name != -1:
                        nl_idx = file_content.find("\n", idx_name)
                        start = (nl_idx + 1) if nl_idx != -1 else idx_name + len(passage_name) + 3
                        passage_body_start_cache[passage_name] = start
                        return start
                    logger.warning(f"找不到段落头: {passage_name}，将使用文件起始作为基准")
                    passage_body_start_cache[passage_name] = 0
                    return 0

                def compute_abs_position(entry):
                    ctx = entry.get('context', '')
                    pos_rel = extract_pos_from_context(ctx)
                    if pos_rel is None:
                        return None
                    if is_js_file:
                        return pos_rel  # JS 的 POS 为文件绝对位置
                    # Twee 的 POS 为段落正文内相对位置，需要加上段落正文起点
                    passage_name = get_passage_name_from_key(entry['key'])
                    return find_passage_body_start(passage_name) + pos_rel

                # 预计算每个词条的绝对位置，并基于该位置排序
                positions_by_key = {}
                for entry in pzdata:
                    abs_pos = compute_abs_position(entry)
                    if abs_pos is None:
                        # 尽量不依赖 fetch 的 position；但为保证健壮性，提供兆底
                        if entry['key'] in fetch_data:
                            positions_by_key[entry['key']] = fetch_data[entry['key']]['position']
                            logger.warning(f"{entry['key']} 的 context 中未找到 POS，回退到 fetch 位置")
                        else:
                            positions_by_key[entry['key']] = 10**12  # 放到末尾
                            logger.warning(f"{entry['key']} 无法解析位置，放到末尾处理")
                    else:
                        positions_by_key[entry['key']] = abs_pos

                pzdata.sort(key=lambda x: positions_by_key.get(x['key'], 10**12))
                tempd = {}
                for d in pzdata:
                    if 'stage' not in d or d['stage']!=1:
                        if "过时" in d['original']:continue
                    translation = ""
                    if d['key'] not in fetch_data:
                        logger.warning(f"{d['key']} not exist!")
                        continue
                    else:
                        if not fetch_data[d['key']]['text']:continue
                        if fetch_data[d['key']]['text'] in "'\"`":continue
                        # 使用由 context <<POS:...>> 解析得到的绝对位置
                        position = positions_by_key.get(d['key'], fetch_data[d['key']]['position'])
                        translation = d['translation'] if d['translation'] else fetch_data[d['key']]['text']
                    # if translation.startswith("<br>") and translation!="<br><br>" and translation!="<br>" and "js" not in root:
                    #     if not (file_content[last_idx:position].endswith("<br>")):position+=4
                    #     if "'" not in translation and "\"" not in translation:translation = translation.replace("<br>","<br>\n")
                    #     fetch_data[d['key']]['text'] = fetch_data[d['key']]['text'].replace("<br>","<br>\n")
                    if not translation:translation = fetch_data[d['key']]['text']
                    if "js" not in root:translation = translation.replace("\\n","\n")
                    # if "js" in root and "+" in translation:translation = "\""+translation
                    target_file_parts.append(file_content[last_idx:position])
                    target_file_parts.append(translation)
                    # if d['key']=="macros_73":print([file_content[last_idx],file_content[position],translation])
                    # if position!=fetch_data[d['key']]['position']:position-=4
                    # delta_index += (len(d['range']) - len(translation))
                    last_idx = position+len(fetch_data[d['key']]['text'])
                    if last_idx-1>=len(file_content):print(translation)
                    if file_content[last_idx-1]!=fetch_data[d['key']]['text'][-1]:
                        if file_content[last_idx]==fetch_data[d['key']]['text'][-1]:
                            last_idx += 1
                        elif last_idx+1<len(file_content) and file_content[last_idx+1]==fetch_data[d['key']]['text'][-1]:
                            last_idx = position+len(fetch_data[d['key']]['text'])+1
                    # if idx%1000==0:logger.info(f"replacing {idx+1}/{len(translation_files[zip_filename])}")
                    idx += 1

                target_file_parts.append(file_content[last_idx:])
                if "Passage" in root or "Widgets" in root:
                    with open(root.replace('trans','translated_source')+"\\"+file.replace('.json','.twee'),encoding="utf-8",mode="w") as fp:
                        fp.write("".join(target_file_parts))
                elif "js" ==root[-2]+root[-1]:
                    with open(root.replace('trans','translated_source')+"\\"+file.replace('.json','.js'),encoding="utf-8",mode="w") as fp:
                        fp.write("".join(target_file_parts))
                logger.info(f"writed {file} done")

    def convert_to_i18n(self):
        i18n = {"typeB":{"TypeBOutputText":[],"TypeBInputStoryScript":[]}}

        # 完全依赖 trans 中 context 的 <<POS:...>>，不再使用 hash_dict 位置
        def parse_pos_from_context(ctx: str):
            if not ctx:
                return None
            m = re.findall(r'&lt;&lt;POS:(\d+)&gt;&gt;', ctx)
            return int(m[-1]) if m else None

        for root, dirs, files in os.walk(self.transPath):
            for file in files:
                with open(f"{root}\\{file}", "r", encoding="utf-8") as fp:
                    pzdata = json.load(fp)

                is_js_root = ("js" == root[-2]+root[-1])

                # 分组：按目标输出文件名聚合（JS 为 fileprefix.js；Twee 为 PassageName.twee）
                file_trans = {}
                for d in pzdata:
                    if '过时' in d.get('original', ''):
                        continue
                    if is_js_root:
                        # JS：统一按当前物理文件聚合，避免同一文件内被拆为多个组导致 emojiDiffIdx 反复清零
                        filename = file.replace(".json", ".js")
                    else:
                        # Twee：严格按 Passage 名称聚合（不携带 fingerprint/冲突后缀），保证整段落一次累加
                        passage = d['key'].split("_")[0]
                        filename = passage + ".twee"
                    file_trans.setdefault(filename, []).append(d)

                for filename, entries in file_trans.items():
                    emojiDiffIdx = 0
                    if is_js_root:
                        passagename = file.replace(".json","")
                    else:
                        # 取首条的 key 推导段落名
                        passagename = entries[0]['key'].split("_")[0]

                    # 位置排序（缺失 POS 的放最后）
                    entries.sort(key=lambda x: (parse_pos_from_context(x.get('context','')) if parse_pos_from_context(x.get('context','')) is not None else 10**12))

                    for d in entries:
                        # 仅处理 stage==1 的有效翻译
                        if d.get('stage', 1) != 1:
                            if "过时" in d.get('original', ''):
                                continue
                            for char in d.get('original', ''):
                                if emoji.is_emoji(char):
                                    emojiDiffIdx += 1
                            continue
                        if d.get('original', '') == d.get('translation', ''):
                            for char in d.get('original', ''):
                                if emoji.is_emoji(char):
                                    emojiDiffIdx += 1
                            continue

                        pos = parse_pos_from_context(d.get('context',''))
                        if pos is None:
                            logger.warning(f"{d['key']} 的 context 未包含 POS，跳过")
                            for char in d.get('original', ''):
                                if emoji.is_emoji(char):
                                    emojiDiffIdx += 1
                            continue

                        if not is_js_root:
                            # Twee：POS 为段落正文内相对位置
                            d['original'] = d['original'].replace("\\n","\n")
                            d['translation'] = d['translation'].replace("\\n","\n")

                            orilist = re.split(r'(?<!\\)\n', d['original'])
                            translist = re.split(r'(?<!\\)\n', d['translation'])
                            if 'StreamingWidgets' in passagename:print(pos,emojiDiffIdx)
                            if len(orilist) != len(translist):
                                logger.error(f"{d['key']} \\n error!")
                                i18n['typeB']['TypeBInputStoryScript'].append({
                                    "pos": pos + emojiDiffIdx,
                                    "pN": passagename.replace(" [widget]",""),
                                    "f": d['original'],
                                    "t": d['translation']
                                })
                                for char in d['original']:
                                    if emoji.is_emoji(char):
                                        emojiDiffIdx += 1
                                continue

                            linepos = pos
                            for i in range(len(translist)):
                                if orilist[i].strip() == translist[i].strip():
                                    linepos += len(orilist[i]) + 1
                                else:
                                    lineidx = 0
                                    for j in range(len(orilist[i])):
                                        if orilist[i][j].strip():
                                            lineidx = j
                                            break
                                    i18n['typeB']['TypeBInputStoryScript'].append({
                                        "pos": linepos + lineidx + emojiDiffIdx,
                                        "pN": passagename.replace(" [widget]",""),
                                        "f": orilist[i].strip(),
                                        "t": translist[i].strip()
                                    })
                                    linepos += len(orilist[i]) + 1
                                emojiDiffIdx += len(emoji.emoji_list(orilist[i]))
                        else:
                            # JS：POS 为文件内绝对位置
                            d['original'] = d['original'].replace("\\n","\n")
                            d['translation'] = d['translation'].replace('\\\\n',"▲").replace("\\n","\n")

                            orilist = re.split(r'(?<!\\)\n', d['original'])
                            translist = re.split(r'(?<!\\)\n', d['translation'])
                            if len(orilist) != len(translist):
                                logger.error(f"{d['key']} \\n error!")
                                i18n['typeB']['TypeBOutputText'].append({
                                    "pos": pos + emojiDiffIdx,
                                    "f": d['original'].replace("▲","\\n"),
                                    "t": d['translation'].replace("▲","\\n"),
                                    "fileName": passagename + ".js",
                                    "js": True
                                })
                                for char in d['original']:
                                    if emoji.is_emoji(char):
                                        emojiDiffIdx += 1
                                continue

                            linepos = pos
                            for i in range(len(translist)):
                                if orilist[i].strip() == translist[i].strip():
                                    linepos += len(orilist[i]) + 1
                                else:
                                    lineidx = 0
                                    for j in range(len(orilist[i])):
                                        if orilist[i][j].strip():
                                            lineidx = j
                                            break
                                    i18n['typeB']['TypeBOutputText'].append({
                                        "pos": linepos + lineidx + emojiDiffIdx,
                                        "f": orilist[i].strip().replace("▲","\\n"),
                                        "t": translist[i].strip().replace("▲","\\n"),
                                        "fileName": passagename + ".js",
                                        "js": True
                                    })
                                    linepos += len(orilist[i]) + 1
                                emojiDiffIdx += len(emoji.emoji_list(orilist[i]))

        with open(self.translatedPath/"i18n.json",encoding="utf-8",mode="w") as fp:
            fp.write(json.dumps(i18n,ensure_ascii=False))
