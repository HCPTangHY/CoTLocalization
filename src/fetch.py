from .consts import *
from .log import logger
from .parseTwee import TweeParser
from .parseTweev2 import TweeParserV2
from .parseJS import JSTextExtractor
from .parseJSv2 import JSParserV2

import ujson as json
import os,shutil,re,numpy,difflib,filecmp,rapidfuzz

class Fetcher:
    def __init__(self,version):
        self.version = version
        self.sourcePath = DIR_SOURCE/self.version
        self.fetchPath = DIR_FETCH/self.version
        self.margeSourcePath = DIR_MARGE_SOURCE/self.version
        self.pzoriPath = DIR_PZ_ORIGIN/self.version
        pass
    def _split_by_case(self,name):
        return re.findall('[A-Z][a-z]*', name)
    def marge_source(self):
        if self.margeSourcePath.exists():
            shutil.rmtree(self.margeSourcePath)
        os.makedirs(self.margeSourcePath/"Passages", exist_ok=True)
        def camel_case_split(identifier):
            matches = re.finditer('.+?(?:(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])|$)', identifier)
            return [m.group(0) for m in matches]

        def process_files():
            files = [f for f in os.listdir(self.sourcePath/"Passages") if os.path.isfile(os.path.join(self.sourcePath/"Passages", f))]
            grouped_files = {}

            for file in files:
                # 移除文件扩展名
                name_without_ext = os.path.splitext(file)[0]
                
                # 大写分段
                segments = camel_case_split(name_without_ext)
                
                # 使用第一个段作为键来分组文件
                key = segments[0] if segments[0]!="Event" else "Event"+segments[1]
                if key not in grouped_files:
                    grouped_files[key] = []
                grouped_files[key].append((file, segments))

            # 处理每组文件
            for key, file_list in grouped_files.items():
                with open(os.path.join(self.margeSourcePath/"Passages", f"{key}.twee" if not key.endswith('.twee') else key), 'w', encoding='utf-8') as f:
                    for original_file, segments in file_list:
                        # 写入原始文件名和分段结果
                        with open(os.path.join(self.sourcePath/"Passages", original_file), 'r', encoding='utf-8') as original_fp:
                            content = original_fp.read()
                        f.write(f"{content}\n\n")

            logger.info(f"处理完成！")
        process_files()
        # 获取目录中所有文件
        # files = [f for f in os.listdir(self.sourcePath/"Passages") if os.path.isfile(os.path.join(self.sourcePath/"Passages", f))]
        # # 按前缀分组
        # groups = {}
        # for file in files:
        #     parts = self._split_by_case(file)
        #     if len(parts) > 1:
        #         prefix = ''.join(parts[:-1])
        #     else:
        #         prefix = file  # 使用整个文件名作为前缀
        #     if prefix not in groups:
        #         groups[prefix] = []
        #     groups[prefix].append(file)

        # # 在现有分组基础上再次合并
        # merged_groups = {}
        # for prefix, group_files in groups.items():
        #     found_match = False
        #     for existing_prefix in list(merged_groups.keys()):
        #         if prefix.startswith(existing_prefix) or existing_prefix.startswith(prefix):
        #             # 选择更长的前缀作为新的键
        #             new_prefix = max(prefix, existing_prefix, key=len)
        #             if new_prefix in merged_groups:
        #                 merged_groups[new_prefix].extend(group_files)
        #             else:
        #                 merged_groups[new_prefix] = merged_groups.pop(existing_prefix) + group_files
        #             found_match = True
        #             break
        #     if not found_match:
        #         merged_groups[prefix] = group_files

        # # 确保所有原始文件都被包含
        # for file in files:
        #     if not any(file in group for group in merged_groups.values()):
        #         merged_groups[file] = [file]
        # groups = merged_groups

        # # 合并每组文件
        # for prefix, group_files in groups.items():
        #     merged_content = ""
        #     for file in group_files:
        #         with open(os.path.join(self.sourcePath/"Passages", file), 'r', encoding='utf-8') as f:
        #             content = f.read()
        #             merged_content += content + "\n\n"
        #     # 写入合并后的文件
        #     with open(os.path.join(self.margeSourcePath/"Passages", f"{prefix}.twee" if not prefix.endswith('.twee') else prefix), 'w', encoding='utf-8') as f:
        #         f.write(merged_content)
    def fetch_source(self):
        if self.fetchPath.exists():
            shutil.rmtree(self.fetchPath)
        os.makedirs(self.fetchPath/"Passages", exist_ok=True)
        hash_dict = {}
        for root, dirs, files in os.walk(self.margeSourcePath):
            for d in dirs:
                if not os.path.exists(self.fetchPath/d):
                    os.makedirs(self.fetchPath/d)
            for file in files:
                # if "Encounter" in file:continue
                logger.info(f"parsing {file}")
                hash_dict[file] = {}
                if file.endswith(".twee"):
                    with open(f"{root}/{file}", "r", encoding="utf-8") as fp:
                        parser = TweeParser()
                        parser.parse(fp.read())
                    parser.extracted_texts.sort(key=lambda x:x['position'])
                    fetchData = {}
                    for d in parser.extracted_texts:
                        fetchData[d['id']] = d
                    with open(root.replace("marge_source","fetch")+"/"+file.replace('.twee','.json'),encoding="utf-8",mode="w+") as fp:
                        fp.write(json.dumps(fetchData,ensure_ascii=False))
        os.makedirs(self.fetchPath/"Widgets", exist_ok=True)
        for root, dirs, files in os.walk(self.sourcePath/"Widgets"):
            for d in dirs:
                if not os.path.exists(self.fetchPath/d):
                    os.makedirs(self.fetchPath/d)
            for file in files:
                hash_dict[file] = {}
                logger.info(f"parsing {file}")
                if file.endswith(".twee"):
                    with open(f"{root}/{file}", "r", encoding="utf-8") as fp:
                        parser = TweeParser()
                        parser.parse(fp.read())
                    parser.extracted_texts.sort(key=lambda x:x['position'])
                    fetchData = {}
                    for d in parser.extracted_texts:
                        fetchData[d['id']] = d
                    with open(root.replace("source","fetch")+"/"+file.replace('.twee','.json'),encoding="utf-8",mode="w+") as fp:
                        fp.write(json.dumps(fetchData,ensure_ascii=False))
        os.makedirs(self.fetchPath/"js", exist_ok=True)
        for root, dirs, files in os.walk(self.sourcePath/"js"):
            for d in dirs:
                if not os.path.exists(self.fetchPath/d):
                    os.makedirs(self.fetchPath/d)
            for file in files:
                hash_dict[file] = {}
                logger.info(f"parsing {file}")
                if file.endswith(".js"):
                    with open(f"{root}/{file}", "r", encoding="utf-8") as fp:
                        parser = JSParserV2()
                        parser.parse(fp.read())
                    parser.extracted_texts.sort(key=lambda x:x['position'])
                    fetchData = {}
                    for d in parser.extracted_texts:
                        fetchData[f"{file.replace('.js','')}_{d['id']}"] = d
                    with open(root.replace("source","fetch")+"/"+file.replace('.js','.json'),encoding="utf-8",mode="w+") as fp:
                        fp.write(json.dumps(fetchData,ensure_ascii=False))
        with open(self.fetchPath/"hash_dict.json", "w", encoding="utf-8") as fp:
            fp.write(json.dumps(hash_dict,ensure_ascii=False))
    def position_update(self):
        with open(self.fetchPath/"hash_dict.json", "r", encoding="utf-8") as fp:
            hash_dict = json.loads(fp.read())
        newhash_dict = {}
        os.makedirs(DIR_FETCH/(self.version+"-changed")/"Passages", exist_ok=True)
        for root, dirs, files in os.walk(self.margeSourcePath/'Passages'):
            for file in files:
                # logger.info(f"parsing {file}")
                try:
                    with open(f"{self.fetchPath}/Passages/{file.replace('.twee','.json')}", "r", encoding="utf-8") as fp:
                        fetchData = json.loads(fp.read())
                except:
                    fetchData = {}
                with open(f"{root}/{file}", "r", encoding="utf-8") as fp:
                    parser = TweeParser()
                    parser.parse(fp.read())
                # parser.extracted_texts.sort(key=lambda x:x['position'])
                # newhash_dict = {d['hash']:{"id":d['id'],"position":d['position']} for d in parser.extracted_texts}
                newfileFlag = False
                oldfileFlag = False
                newfetchData = {}
                hashUsed = []
                for d in fetchData:
                    newfetchData[d] = fetchData[d]
                for d in fetchData:
                    oldpassage = '_'.join(d.split("_")[:-1])
                    # hash_dict_now = hash_dict[oldpassage+('.js' if "js" in root else '.twee')]
                    if 'stage' in fetchData[d] and fetchData[d]['stage'] == 9:continue
                    find = False
                    for i in range(len(parser.extracted_texts)):
                        if parser.extracted_texts[i]['hash'] == fetchData[d]['hash'] and fetchData[d]['hash'] not in hashUsed:
                            find = True
                            passagename = '_'.join(parser.extracted_texts[i]['id'].split("_")[:-1])
                            if parser.extracted_texts[i]['position']!= fetchData[d]['position']:
                                logger.warning(f"position updated for {d}")
                                fetchData[d]['position'] = parser.extracted_texts[i]['position']
                                oldfileFlag = True
                            if d=="DisplayNPC_11":
                                print(oldpassage!= passagename)
                            if oldpassage!= passagename:
                                logger.warning(f"passage name updated for {d}")
                                idx = 0
                                for d2 in fetchData[d]:
                                    nowpassagename = "_".join(d2.split("_")[:-1])
                                    id = fetchData[d]['id'].split("_")[-1]
                                    if int(id) >= idx and nowpassagename == passagename:
                                        idx = int(id)+1
                                newfetchData[f"{passagename}_{idx}"] = fetchData[d]
                                newfetchData[d]['stage'] = 9
                                fetchData[d]['stage'] = 9
                                newfileFlag = True
                                oldfileFlag = True
                            # hashUsed.append(fetchData[d]['hash'])
                            break
                    if not find:
                        logger.error(f"no match for {d}")
                        fetchData[d]['stage'] = 9
                        oldfileFlag = True
                if fetchData=={}:
                    for d in parser.extracted_texts:
                        fetchData[d['id']] = d
                    with open(f"{DIR_FETCH/(self.version+'-changed')/'Passages'}/{file.replace('.twee','.json')}",encoding="utf-8",mode="w+") as fp:
                        fp.write(json.dumps(fetchData,ensure_ascii=False))
                if newfileFlag:
                    with open(f"{DIR_FETCH/(self.version+'-changed')/'Passages'}/{file.replace('.twee','.json')}",encoding="utf-8",mode="w+") as fp:
                        fp.write(json.dumps(newfetchData,ensure_ascii=False))
                if oldfileFlag:
                    with open(root.replace("marge_source","fetch")+"/"+file.replace('.twee','.json'),encoding="utf-8",mode="w+") as fp:
                        fp.write(json.dumps(fetchData,ensure_ascii=False))
    def hash_update(self):
        # with open(self.fetchPath/"hash_dict.json", "r", encoding="utf-8") as fp:
        #     hash_dict = json.loads(fp.read())
        hash_dict = {}
        for root, dirs, files in os.walk(self.fetchPath):
            for file in files:
                if "hash_dict" in file:continue
                logger.info(f"updating {file}")
                with open(f"{root}/{file}", "r", encoding="utf-8") as fp:
                    filedata = json.loads(fp.read())
                newhash_dict = {}
                nowpassage = ""
                for d in filedata:
                    ids = d.split("_")
                    ids.pop(-1)
                    passagename = "_".join(ids)
                    if not nowpassage:nowpassage = passagename
                    id = d
                    if d=="DisplayNPC_71":print(filedata[d]['hash'])
                    # if 'type' in filedata[d] and filedata[d]['type'] in "passage_name":continue
                    if 'stage' in filedata[d] and filedata[d]['stage']== 9: continue
                    if passagename+('.js' if "js" in root else '.twee') in hash_dict:
                        hash_dict[passagename+('.js' if "js" in root else '.twee')][filedata[d]['hash']] = {"id":id,"position":filedata[d]['position'],"type":filedata[d]['type']}
                    else:
                        hash_dict[passagename+('.js' if "js" in root else '.twee')] = {filedata[d]['hash']:{"id":id,"position":filedata[d]['position'],"type":filedata[d]['type']}}
                #     newhash_dict[filedata[d]['hash']] = {"id":id,"position":filedata[d]['position'],"type":filedata[d]['type']}
                # if newhash_dict and nowpassage!="":
                #     hash_dict[nowpassage+".js" if "js" in root else nowpassage+".twee"] = newhash_dict
        with open(self.fetchPath/"hash_dict.json", "w", encoding="utf-8") as fp:
            fp.write(json.dumps(hash_dict,ensure_ascii=False))
    def convert_to_pz(self):
        # if self.pzoriPath.exists():
        #     shutil.rmtree(self.pzoriPath)
        # os.makedirs(self.pzoriPath, exist_ok=True)
        for root, dirs, files in os.walk(self.fetchPath):
            for d in dirs:
                if not os.path.exists(self.pzoriPath/d):
                    os.makedirs(self.pzoriPath/d)
            for file in files:
                if "hash_dict" in file:continue
                logger.info(f"convert {file}")
                with open(f"{root}/{file}", "r", encoding="utf-8") as fp:
                    filedata = json.loads(fp.read())
                pzdata = []
                for d in filedata:
                    key = d
                    d = filedata[d]
                    if ('type' in d and d['type'] in "passage_name") or (not isinstance(d['id'],int) and d['id'].endswith("_0") and "js" in root):continue
                    if 'stage' in d and d['stage'] == 9:
                        pzdata.append({
                            "key":key if ("Passages" in root) or ("Widgets" in root) or ("_" in key) else f"{file.replace('.json','')}_{d['id']}",
                            "original":d['text']+"过时",
                            "context":d['context'],
                            "position":d['position'],
                            "stage":9
                        })
                    else:
                        pzdata.append({
                            "key":key if ("Passages" in root) or ("Widgets" in root) or ("_" in key) else f"{file.replace('.json','')}_{d['id']}",
                            "original":d['text'],
                            "context":d['context'],
                            "position":d['position']
                        })
                # if "database_names" in file or "worldgen" in file:
                #     pzdata = numpy.array(pzdata)
                #     pzdata = numpy.array_split(pzdata,3)
                #     for i in range(len(pzdata)):
                #         with open(root.replace("fetch","pz_origin")+"/"+file.replace(".json",f"_{i}.json"),encoding="utf-8",mode="w+") as fp:
                #             fp.write(json.dumps(pzdata[i].tolist(),ensure_ascii=False))
                # else:
                with open(root.replace("fetch","pz_origin")+"/"+file,encoding="utf-8",mode="w+") as fp:
                    fp.write(json.dumps(pzdata,ensure_ascii=False))
    def pz_token_update(self):
        logger.add('out.log')
        for root, dirs, files in os.walk(self.fetchPath):
            for file in files:
                # if '\js' in root :continue
                logger.info(f"reading {file}")
                try:
                    with open(f"{root}/{file}", "r", encoding="utf-8") as fp:
                        filedata = json.loads(fp.read())
                    with open(f"{root.replace('fetch','trans')}/{file}", "r", encoding="utf-8") as fp:
                        pzdata = json.loads(fp.read())
                    with open(f"{root.replace('fetch','pz_origin')}/{file}", "r", encoding="utf-8") as fp:
                        pzoridata = json.loads(fp.read())
                except:
                    logger.error(f"no file {file}")
                    continue
                # if len(pzdata)==len(pzoridata):
                #     allpass = True
                #     for i in range(len(pzdata)):
                #         if pzdata[i]['key'] != pzoridata[i]['key'] or pzdata[i]['original'].replace("\\n","\n")!=pzoridata[i]['original']:
                #             allpass = False
                #             break
                # if allpass:continue
                pzori_dict = {}
                for i, item in enumerate(pzoridata):
                    if item['original'] not in pzori_dict:
                        pzori_dict[item['original']] = []
                    pzori_dict[item['original']].append((i, item))

                result = []
                used_indices = set()

                for i, item1 in enumerate(pzdata):
                    if item1['original'].replace("\\n","\n") in pzori_dict:
                        # 找到索引差最小的匹配项
                        matches = pzori_dict[item1['original'].replace("\\n","\n")]
                        best_match = min(matches, key=lambda x: abs(x[0] - i))
                        
                        # 更新 key 并添加到结果
                        item1['key'] = best_match[1]['key']
                        item1['context'] = best_match[1]['context'].replace("\\n","\n")
                        result.append(item1)
                        used_indices.add(best_match[0])
                    elif 'context' in item1 and item1['context'].replace("\\n","\n") in pzori_dict:
                        # 处理 context 的情况
                        matches = pzori_dict[item1['context'].replace("\\n","\n")]
                        best_match = min(matches, key=lambda x: abs(x[0] - i))
                        
                        item1['key'] = best_match[1]['key']
                        item1['original'] = best_match[1]['original'].replace("\\n","\n")
                        item1['context'] = best_match[1]['context'].replace("\\n","\n")
                        result.append(item1)
                        used_indices.add(best_match[0])

                # 添加文件2中未使用的项
                for i, item in enumerate(pzoridata):
                    if i not in used_indices:
                        result.append(item.copy())

                # 创建文件2的键到索引的映射
                pzoridata_key_to_index = {item['key']: i for i, item in enumerate(pzoridata)}

                # 使用更安全的排序方法
                def safe_sort_key(item):
                    return pzoridata_key_to_index.get(item['key'])

                result.sort(key=safe_sort_key)

                resultuni=[]
                for i in result:
                    if i not in resultuni:
                        resultuni.append(i)
                with open(f"{root.replace('fetch','trans')}/{file}", "w", encoding="utf-8") as fp:
                    fp.write(json.dumps(resultuni,ensure_ascii=False))
    
    def compare_source(self,version2):
        # if (DIR_FETCH/version2).exists():
        #     shutil.rmtree(DIR_FETCH/version2)
        os.makedirs(DIR_FETCH/version2/"Passages", exist_ok=True)
        os.makedirs(DIR_FETCH/version2/"js", exist_ok=True)
        os.makedirs(DIR_FETCH/version2/"Widgets", exist_ok=True)
        with open(self.fetchPath/"hash_dict.json", "r", encoding="utf-8") as fp:
            hash_dict = json.loads(fp.read())
        def compare_directories(dir1, dir2):
            comparison = filecmp.dircmp(dir1, dir2)
            # 打印不同的文件
            print("不同的文件:")
            for name in comparison.diff_files + comparison.right_only:
                dir = str(dir1).split("/")[-1]
                print(f"- {name}")
                hash_file = hash_dict[name] if name in hash_dict else {}
                used_new_string = []
                new_string = []
                newfetch = {}
                new_string_queue = []
                try:
                    if name.endswith('.js'):
                        with open(self.fetchPath/dir/name.replace(".js",".json"), "r", encoding="utf-8") as fp:
                            oldfetch = json.loads(fp.read())
                    else:
                        with open(self.fetchPath/dir/name.replace(".twee",".json"), "r", encoding="utf-8") as fp:
                            oldfetch = json.loads(fp.read())
                except:
                    logger.info(f"new file {name}")
                    oldfetch = {}
                with open(dir2/name, "r", encoding="utf-8") as fp:
                    if name.endswith('.js'):
                        parser = JSParserV2()
                    else:
                        parser = TweeParser()
                    parser.parse(fp.read())
                parser.extracted_texts.sort(key=lambda x:x['position'])
                newhash_file = {parser.extracted_texts[d]['hash']:{"id":parser.extracted_texts[d]['id'],"position":parser.extracted_texts[d]['position']} for d in range(len(parser.extracted_texts))}
                newdata = {}
                for d in parser.extracted_texts:
                    newdata[d['id']] = d
                newfetch = {}
                delta_postion = 0
                for d in oldfetch:
                    # if "roomtype" in name:print(oldfetch[d]['hash'],newhash_file)
                    passagename = "_".join(d.split("_")[:-1]) if not name.endswith('.js') else name.replace(".js","")
                    hashFound = False
                    for hash in newhash_file:
                        nowpassagename = "_".join(newhash_file[hash]['id'].split("_")[:-1]) if not name.endswith('.js') else name.replace(".js","")
                        if hash == oldfetch[d]['hash'] and passagename == nowpassagename:
                            newfetch[d] = newdata[newhash_file[hash]['id']]
                            if newhash_file[oldfetch[d]['hash']]['position'] != oldfetch[d]['position']+delta_postion:
                                logger.error(f"位置不同：{oldfetch[d]['id']} {delta_postion} 差距{newhash_file[oldfetch[d]['hash']]['position'] - oldfetch[d]['position']+delta_postion},{newhash_file[oldfetch[d]['hash']]['position']},{oldfetch[d]['position']}")
                            used_new_string.append(newhash_file[oldfetch[d]['hash']]['id'])
                            if oldfetch[d]['position']+delta_postion != newhash_file[oldfetch[d]['hash']]['position']:
                                delta_postion = newhash_file[oldfetch[d]['hash']]['position'] - oldfetch[d]['position']
                                logger.warning(f"相同更新位置：{oldfetch[d]['id']} {delta_postion} {oldfetch[d]['position']+delta_postion} {newhash_file[oldfetch[d]['hash']]['position']}")
                            hashFound = True
                            break
                    if not hashFound:
                        find = False
                        for i in newdata:
                            nowpassagename = "_".join(i.split("_")[:-1]) if not name.endswith('.js') else name.replace(".js","")
                            if newdata[i]['position'] == oldfetch[d]['position']+delta_postion and passagename == nowpassagename:
                                find = True
                                logger.info(f"相同更新位置：{oldfetch[d]['id']} {delta_postion} {oldfetch[d]['position']+delta_postion} {newdata[i]['position']},长度{len(newdata[i]['text']) != len(oldfetch[d]['text'])}")
                                if len(newdata[i]['text']) != len(oldfetch[d]['text']):
                                    delta_postion = newdata[i]['position'] - oldfetch[d]['position'] + len(newdata[i]['text']) - len(oldfetch[d]['text'])
                                    logger.warning(f"不同更新位置：{oldfetch[d]['id']} {delta_postion}")
                                newfetch[d] = newdata[i]
                                used_new_string.append(newdata[i]['id'])
                                break
                        if not find:
                            newfetch[d] = oldfetch[d].copy()
                            newfetch[d]['stage'] = 9
                            logger.warning(f"找不到匹配项：{oldfetch[d]['id']} {delta_postion} {oldfetch[d]['position']+delta_postion}")
                rest_new_string = [newdata[d]['id'] for d in newdata if newdata[d]['id'] not in used_new_string]
                for i in range(len(rest_new_string)):
                    passagename = "_".join(rest_new_string[i].split("_")[:-1]) if not name.endswith('.js') else name.replace(".js","")
                    idx = 0
                    for d in newfetch:
                        nowpassagename = "_".join(d.split("_")[:-1])
                        id = d.split("_")[-1]
                        if int(id) >= idx and nowpassagename == passagename:
                            idx = int(id)+1
                        # print(nowpassagename == passagename,id,idx)
                    for j in newdata:
                        if newdata[j]['id'] == rest_new_string[i]:
                            data = newdata[j]
                    if name.endswith('.js'):newfetch[f"{name.replace('.js','')}_{idx}"] = data
                    else:newfetch[f"{passagename}_{idx}"] = data
                    logger.info(f"新增项：{passagename}_{idx}")
                with open(DIR_FETCH/version2/dir/name.replace(".js",".json").replace(".twee",".json"), "w", encoding="utf-8") as fp:
                    fp.write(json.dumps(newfetch,ensure_ascii=False))
                
                hash_dict[name] = {newfetch[d]['hash']:{"id":newfetch[d]['id'],"position":newfetch[d]['position']} for d in newfetch}
            with open(DIR_FETCH/version2/"hash_dict.json", "w", encoding="utf-8") as fp:
                fp.write(json.dumps(hash_dict,ensure_ascii=False))

        compare_directories(self.margeSourcePath/'Passages', DIR_MARGE_SOURCE/version2/'Passages')
        compare_directories(self.sourcePath/'Widgets', DIR_SOURCE/version2/'Widgets')
        compare_directories(self.sourcePath/'js', DIR_SOURCE/version2/'js')

    def compare_source_new(self,version2):
        # 基于 parseTwee/parseJSv2 的“键(id)”进行对比与合并，不再使用 hash 匹配
        os.makedirs(DIR_FETCH/version2/"Passages", exist_ok=True)
        os.makedirs(DIR_FETCH/version2/"js", exist_ok=True)
        os.makedirs(DIR_FETCH/version2/"Widgets", exist_ok=True)

        def compare_directories_by_key(dir1, dir2):
            comparison = filecmp.dircmp(dir1, dir2)
            # 打印不同和新增的文件
            print("不同的文件(基于Key):")
            for name in comparison.diff_files + comparison.right_only:
                dir = str(dir1).split("/")[-1]
                print(f"- {name}")

                # 读取旧版抓取数据
                try:
                    if name.endswith('.js'):
                        with open(self.fetchPath/dir/name.replace(".js",".json"), "r", encoding="utf-8") as fp:
                            oldfetch = json.loads(fp.read())
                    else:
                        with open(self.fetchPath/dir/name.replace(".twee",".json"), "r", encoding="utf-8") as fp:
                            oldfetch = json.loads(fp.read())
                except:
                    logger.info(f"new file {name}")
                    oldfetch = {}

                # 解析新版源码
                with open(dir2/name, "r", encoding="utf-8") as fp:
                    if name.endswith('.js'):
                        parser = JSParserV2()
                    else:
                        parser = TweeParser()
                    parser.parse(fp.read())
                parser.extracted_texts.sort(key=lambda x:x['position'])

                # 构建“键”为主的新数据映射
                newdata = {}
                if name.endswith('.js'):
                    fileprefix = name.replace(".js","")
                    for d in parser.extracted_texts:
                        key = f"{fileprefix}_{d['id']}"
                        newdata[key] = d
                else:
                    for d in parser.extracted_texts:
                        newdata[d['id']] = d

                # 基于 Key 的合并逻辑
                newfetch = {}
                used_new_keys = set()

                # 旧键优先保留：存在则更新为新文本，不存在则标记为过时(stage=9)
                for key, val in oldfetch.items():
                    if key in newdata:
                        newfetch[key] = newdata[key]
                        used_new_keys.add(key)
                    else:
                        entry = val.copy()
                        entry['stage'] = 9
                        newfetch[key] = entry
                        logger.warning(f"找不到匹配项（按键）：{key}")

                # 加入新增键
                for key, val in newdata.items():
                    if key not in used_new_keys and key not in newfetch:
                        newfetch[key] = val
                        logger.info(f"新增项（按键）：{key}")

                # 写出结果
                out_path = DIR_FETCH/version2/dir/name.replace(".js",".json").replace(".twee",".json")
                with open(out_path, "w", encoding="utf-8") as fp:
                    fp.write(json.dumps(newfetch, ensure_ascii=False))

        # 三类目录逐一对比
        compare_directories_by_key(self.margeSourcePath/'Passages', DIR_MARGE_SOURCE/version2/'Passages')
        compare_directories_by_key(self.sourcePath/'Widgets', DIR_SOURCE/version2/'Widgets')
        compare_directories_by_key(self.sourcePath/'js', DIR_SOURCE/version2/'js')

    def clean_obsolete_entries(self):
        for root, dirs, files in os.walk(self.fetchPath):
            for file in files:
                if file == "hash_dict.json":  # 跳过hash字典文件
                    continue

                file_path = os.path.join(root, file)
                logger.info(f"Processing {file_path} for obsolete entries")
                try:
                    # 读取文件内容
                    with open(file_path, "r", encoding="utf-8") as fp:
                        try:
                            data = json.load(fp)
                        except json.JSONDecodeError:
                            logger.error(f"Skipping invalid JSON file: {file_path}")
                            continue

                    if not isinstance(data, dict):
                        logger.warning(f"Skipping file with non-dictionary root structure: {file_path}")
                        continue

                    cleaned_data = {
                        key: value for key, value in data.items()
                        if isinstance(value, dict) and value.get("stage") != 9
                    }
                    # 如果数据有变化，则写回文件
                    if len(cleaned_data) != len(data):
                        logger.info(f"Removed {len(data) - len(cleaned_data)} obsolete entries from {file_path}")
                        with open(file_path, "w", encoding="utf-8") as fp:
                            json.dump(cleaned_data, fp, ensure_ascii=False, indent=2)

                except FileNotFoundError:
                     logger.error(f"File not found during cleanup: {file_path}")
                except Exception as e:
                    logger.error(f"Error processing {file_path}: {str(e)}")

        logger.info("Obsolete entries cleanup completed")