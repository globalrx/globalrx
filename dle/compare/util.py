from datetime import datetime
import diff_match_patch as dmp_module
import gensim
from gensim.parsing.preprocessing import remove_stopwords
from .models import *

SECTION_NAMES_DICT = {
    'INDICATIONS': 'Indications',
    'CONTRA': 'Contraindications',
    'WARN': 'Warnings',
    'PREG': 'Pregnancy',
    'POSE': 'Posology',
    'INTERACT': 'Interactions',
    'DRIVE': 'Effects on driving',
    'SIDE': 'Side effects',
    'OVER': 'Overdose',
    "('INDICATIONS', 'Indications')": 'Indications',
    "('CONTRA', 'Contraindications')": 'Contraindications',
    "('WARN', 'Warnings')": 'Warnings',
    "('PREG', 'Pregnancy')": 'Pregnancy',
    "('POSE', 'Posology')": 'Posology',
    "('INTERACT', 'Interactions')": 'Interactions',
    "('DRIVE', 'Effects on driving')": 'Effects on driving',
    "('SIDE', 'Side effects')": 'Side effects',
    "('OVER', 'Overdose')": 'Overdose',
}

def get_date_obj(str_date):
    month, day_year = str_date.split('.')
    day, year = day_year.split(',')
    return datetime.strptime(month + ' ' + day + ' ' + year, '%b %d %Y')

def map_section_names(str):
    return SECTION_NAMES_DICT[str]

def get_diff_for_diff_versions(text1, text2):
    dmp = dmp_module.diff_match_patch()
    diff = dmp.diff_main(text1, text2)
    dmp.diff_cleanupSemantic(diff)

    diff1 = []
    diff2 = []
    for tuple in diff:
        if tuple[0] in [-1, 0]:
            diff1.append(tuple)
        if tuple[0] in [0, 1]:
            diff2.append(tuple)
    
    return (diff1, diff2)

def get_diff_match_tuples(text_arr, common_index_list, value):
    data = []
    isCommon = False
    arr = []
    length = len(text_arr)
    for i in range(length):
        if i in common_index_list:
            if not isCommon:
                arr_text = ""
                for j in arr:
                    arr_text += text_arr[j] + " "
                data.append((0, arr_text))
                isCommon = True
                arr = []
        else:
            if isCommon:
                arr_text = ""
                for j in arr:
                    arr_text += text_arr[j] + " "
                data.append((value, arr_text))
                isCommon = False
                arr = []
        arr.append(i)

    arr_text = ""
    for j in arr:
        arr_text += text_arr[j] + " "
    data.append((value if isCommon else 0, arr_text))
    return data

def get_diff_for_diff_products(text1, text2):
    text1_arr = text1.split(' ')
    text2_arr = text2.split(' ')
    text1_dict = {value: key for value, key in enumerate(text1_arr)}
    text2_dict = {value: key for value, key in enumerate(text2_arr)}

    # texts with stop word removed (swr)
    text1_swr_arr = remove_stopwords(text1).split(' ')
    text2_swr_arr = remove_stopwords(text2).split(' ')
    common_words = set(text1_swr_arr).intersection(text2_swr_arr)

    # get indeces of common words/phrases
    common_phrases1 = []
    common_phrases2 = []
    for word in common_words:
        listOfKeys1 = [key  for (key, value) in text1_dict.items() if value == word]
        listOfKeys2 = [key  for (key, value) in text2_dict.items() if value == word]

        for i in listOfKeys1:
            for j in listOfKeys2:
                phrase1 = [i]
                phrase2 = [j]
                index1 = i + 1
                index2 = j + 1

                while index1 < len(text1_arr) and index2 < len(text2_arr):
                    if text1_arr[index1] == text2_arr[index2]:
                        phrase1.append(index1)
                        phrase2.append(index2)
                        index1 += 1
                        index2 += 1
                    else:
                        break
                
                index1 = i - 1
                index2 = j - 1
                while index1 >= 0 and index2 >= 0:
                    if text1_arr[index1] == text2_arr[index2]:
                        phrase1 = [index1] + phrase1
                        phrase2 = [index2] + phrase2
                        index1 -= 1
                        index2 -= 1
                    else:
                        break
                
                # only append if common phrase is more one word long
                if len(phrase1) > 1:
                    common_phrases1.append(phrase1)
                    common_phrases2.append(phrase2)

    flat_common_phrases1 = [item for sublist in common_phrases1 for item in sublist]
    flat_common_phrases2 = [item for sublist in common_phrases2 for item in sublist]

    diff1 = get_diff_match_tuples(text1_arr, flat_common_phrases1, -1)
    diff2 = get_diff_match_tuples(text2_arr, flat_common_phrases2, 1)
    return (diff1, diff2)