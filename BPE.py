#-*-coding:utf-8

# https://arxiv.org/abs/1508.07909 Byte-Pair Encoding (BPE)
# https://lovit.github.io/nlp/2018/04/02/wpm/ 참고

import re, collections
import numpy as np # 1.15
import pandas as pd # 0.23
import csv
import time
import os

# word:"abc" => "a b c space_symbol"
def word_split_for_bpe(word, space_symbol='</w>'):
	return ' '.join(list(word)) + ' ' + space_symbol


# word frequency 추출.
def get_word_frequency_dict_from_document(path, space_symbol='</w>', top_k=None):
	word_frequency_dict = {}

	with open(path, 'r', encoding='utf-8') as f:
		for i, sentence in enumerate(f):
			# EOF check
			if sentence == '\n' or sentence == ' ' or sentence == '':
				break
			
			for word in sentence.split():					
				# "abc" => "a b c space_symbol"
				split_word = word_split_for_bpe(word, space_symbol)
				
				# word frequency
				if split_word in word_frequency_dict:
					word_frequency_dict[split_word] += 1
				else:
					word_frequency_dict[split_word] = 1

	if top_k is None:
		return word_frequency_dict
	
	else:
		# top_k frequency word
		sorted_word_frequency_list = sorted(
					word_frequency_dict.items(), # ('key', value) pair
					key=lambda x:x[1], # x: ('key', value), and x[1]: value
					reverse=True
				) # [('a', 3), ('b', 2), ... ] 
		top_k_word_frequency_dict = dict(sorted_word_frequency_list[:top_k])
	
		return top_k_word_frequency_dict

# merge two dictionary
def merge_dictionary(dic_a, dic_b):
	for i in dic_b:
		if i in dic_a:
			dic_a[i] += dic_b[i]
		else:
			dic_a[i] = dic_b[i]
	return dic_a


# 2-gram frequency table 추출.
def get_stats(word_frequency_dict):
	# word_frequency_dict: dictionary
	pairs = collections.defaultdict(int) # tuple form으로 key 사용 가능함.
	for word, freq in word_frequency_dict.items():
		symbols = word.split()
		for i in range(len(symbols)-1):
			pairs[symbols[i],symbols[i+1]] += freq
	
	# tuple을 담고 있는 dictionary 리턴.
	return pairs 

# pairs 중에서 가장 높은 frequency를 갖는 key 리턴.
def check_merge_info(pairs):
	best = max(pairs, key=pairs.get)
	return best

# frequency가 가장 높은 best_pair 정보를 이용해서 단어를 merge.
def merge_word2idx(best_pair, word_frequency_dict):
	# best_pair: tuple ('r','</w>')
	# word_frequency_dict: dictionary
	
	v_out = collections.OrderedDict() # 입력 순서 유지

	bigram = re.escape(' '.join(best_pair))
	p = re.compile(r'(?<!\S)' + bigram + r'(?!\S)')
	for word in word_frequency_dict:
		# 만약 ''.join(best_pair): r</w> 이고, word: 'a r </w>' 이면 w_out은 'a r</w>'가 된다.
		w_out = p.sub(''.join(best_pair), word)
		v_out[w_out] = word_frequency_dict[word]
	return v_out


# from bpe to idx
def make_bpe2idx(word_frequency_dict):
	bpe2idx = {
				'</p>':-1,  # embedding_lookup -1 is 0
				'UNK':0,
				'</g>':1, #go
				'</e>':2 #eos
			}
	idx = 3
	
	idx2bpe = {
				-1:'</p>',
				0:'UNK',
				1:'</g>', #go
				2:'</e>' #eos
			}
	
	for word in word_frequency_dict:
		for bpe in word.split():
			# bpe가 bpe2idx에 없는 경우만 idx 부여.
			if bpe not in bpe2idx:
				bpe2idx[bpe] = idx
				idx2bpe[idx] = bpe
				idx += 1
	return bpe2idx, idx2bpe



def get_bpe_information(word_frequency_dict, num_merges=10):
	#word_frequency_dict = {'l o w </w>' : 1, 'l o w e r </w>' : 1, 'n e w e s t </w>':1, 'w i d e s t </w>':1}
	
	#merge_info: 합친 정보를 기억하고있다가. 나중에 데이터를 같은 순서로만 합치면 똑같이 됨.
	merge_info = collections.OrderedDict() # 입력 순서 유지
	
	word_frequency_dict = collections.OrderedDict(word_frequency_dict) # 입력 순서 유지(cache 구할 때 순서 맞추려고)
	cache = word_frequency_dict.copy() # 나중에 word -> bpe 처리 할 때, 빠르게 하기 위함.

	start = time.time()
	log = 1 # 1000등분마다 찍을것.
	for i in range(num_merges):
		#1000등분마다 로그
		if i % (num_merges / 1000) == 0:
			print( log,'/',1000 , 'time:', time.time()-start )
			log += 1 # 1000등분마다 찍을것.

		pairs = get_stats(word_frequency_dict) # 2gram별 빈도수 추출.
		best = check_merge_info(pairs) # 가장 높은 빈도의 2gram 선정
		word_frequency_dict = merge_word2idx(best, word_frequency_dict) # 가장 높은 빈도의 2gram을 합침.

		#merge 하는데 사용된 정보 저장.
		merge_info[best] = i 
	

	# 빠른 변환을 위한 cache 저장. 기존 word를 key로, bpe 결과를 value로.
	merged_keys = list(word_frequency_dict.keys())
	for i, key in enumerate(cache):
		cache[key] = merged_keys[i]

	# voca 추출.
	bpe2idx, idx2bpe = make_bpe2idx(word_frequency_dict)
	return bpe2idx, idx2bpe, merge_info, cache



def merge_a_word(merge_info, word, cache={}):
	# merge_info: OrderedDict {('s','</w>'):0, ('e', '</w>'):1 ... }
	# word: "c e m e n t </w>" => "ce m e n t<\w>" 되어야 함.
	
	if len(word.split()) == 1:
		return word

	if word in cache:
		return cache[word]
	else:
		bpe_word = word
		for info in merge_info:
			bigram = re.escape(' '.join(info))
			p = re.compile(r'(?<!\S)' + bigram + r'(?!\S)')

			# 만약 ''.join(info): r</w> 이고, bpe_word: 'a r </w>' 이면 w_out은 'a r</w>'가 된다.
			bpe_word = p.sub(''.join(info), bpe_word)

		cache[word] = bpe_word
		return bpe_word



def save_dictionary(path, dictionary):
	np.save(path, dictionary)

def load_dictionary(path):
	data = np.load(path, encoding='bytes').item()
	return data


# 문서를 읽고, bpe 적용. cache 사용할것. apply_bpe에서 사용.
def bpe_to_document(path, out_path, space_symbol='</w>', bpe2idx={}, merge_info=None, cache={}):
	start = time.time()

	cache_len = len(cache)

	# write file
	o = open(out_path, 'w', newline='', encoding='utf-8')
	wr = csv.writer(o, delimiter=' ')

	#bpe = []
	with open(path, 'r', encoding='utf-8') as f:
		for i, sentence in enumerate(f):
			row = []
			if sentence == '\n' or sentence == ' ' or sentence == '':
				break
			
			if (i+1) % 100 == 0:
				print('data:', path, '\trow:', i+1, '\ttime:', time.time()-start)
				save_dictionary('./cache.npy', cache)
				print('save updated cache ./cache.npy', 'size:', len(cache), 'added:', len(cache)-cache_len, '\n')
		

			for word in sentence.split():
				# "abc" => "a b c space_symbol"
				split_word = word_split_for_bpe(word, space_symbol)
				
				# space_symbol: </w>
				# merge_info를 이용해서 merge.  "a b c </w>" ==> "ab c</w>"
				merge = merge_a_word(merge_info, split_word, cache)
				
				# 안합쳐진 부분은 다른 단어로 인식해서 공백기준 split 처리해서 sentence에 extend
				row.extend(merge.split())


			wr.writerow(row)

	o.close()
	print('save', out_path)



def learn_bpe(path_list, out_path_folder, space_symbol='</w>', top_k=None, num_merges=1):
	print('get word frequency dictionary')
	total_word_frequency_dict = {}
	for path in path_list:
		word_frequency_dict = get_word_frequency_dict_from_document(
				path=path, 
				space_symbol=space_symbol, 
				top_k=top_k#None
			) #ok
		merge_dictionary(total_word_frequency_dict, word_frequency_dict)

	save_dictionary('./word_frequency_dictionary.npy', total_word_frequency_dict)
	print('save ./word_frequency_dictionary.npy', 'size:', len(total_word_frequency_dict), '\n')


	print('learn bpe')
	bpe2idx, idx2bpe, merge_info, cache = get_bpe_information(
				total_word_frequency_dict, 
				num_merges=num_merges
			)#100
	
	if not os.path.exists(out_path_folder):
		print("create out_path directory")
		os.makedirs(out_path_folder)

	save_dictionary(out_path_folder+'bpe2idx.npy', bpe2idx)
	save_dictionary(out_path_folder+'idx2bpe.npy', idx2bpe)
	save_dictionary(out_path_folder+'merge_info.npy', merge_info)
	save_dictionary(out_path_folder+'cache.npy', cache)
	print('save bpe2idx.npy', 'size:', len(bpe2idx))
	print('save idx2bpe.npy', 'size:', len(idx2bpe))
	print('save merge_info.npy', 'size:', len(merge_info))
	print('save cache.npy', 'size:', len(cache))



def apply_bpe(path_list, out_list, out_path_folder, space_symbol='</w>', pad_symbol='</p>'):


	print('load bpe info', '\n')
	bpe2idx = load_dictionary(out_path_folder+'bpe2idx.npy')
	merge_info = load_dictionary(out_path_folder+'merge_info.npy')
	cache = load_dictionary(out_path_folder+'cache.npy')

	for i in range(len(path_list)):
		path = path_list[i]
		out_path = out_list[i]

		print('apply bpe', path, out_path)
		bpe_to_document(
					path=path, 
					out_path=out_path_folder+out_path,
					space_symbol=space_symbol, 
					bpe2idx=bpe2idx,
					merge_info=merge_info, 
					cache=cache
				)



path_list = ["../dataset/corpus.tc.en/corpus.tc.en", "../dataset/corpus.tc.de/corpus.tc.de"] # original data1, data2
out_list = ['./bpe_wmt17.en', './bpe_wmt17.de'] # bpe_applied_data1, data2
out_path_folder = './bpe_dataset/'

learn_bpe(path_list, out_path_folder, space_symbol='</w>', top_k=None, num_merges=37000)
apply_bpe(path_list, out_list, out_path_folder, space_symbol='</w>', pad_symbol='</p>')

test_path_list = [
			'dataset/dev.tar/newstest2014.tc.en',
			'dataset/dev.tar/newstest2015.tc.en',
			'dataset/dev.tar/newstest2016.tc.en',
		]
test_out_list = [
			'./bpe_newstest2014.en', 
			'./bpe_newstest2015.en', 
			'./bpe_newstest2016.en', 
		] 
		
apply_bpe(test_path_list, test_out_list, out_path_folder, space_symbol='</w>', pad_symbol='</p>')
