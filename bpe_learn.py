import argparse
import os
import bpe_module.learn_BPE as learn_BPE
import bpe_module.apply_BPE as apply_BPE

parser = argparse.ArgumentParser(description='file path')
parser.add_argument('-train_path', required=True, nargs='+')
parser.add_argument('-voca_out_path', required=True)
parser.add_argument('-bpe_out_path', required=True, nargs='+')
parser.add_argument('-train_voca_threshold', required=True) # 빠른 학습을 위해 일정 빈도수 이하의 단어는 bpe learn에 참여시키지 않음.
parser.add_argument('-final_voca_size', required=True)
parser.add_argument('-num_merges', required=True)
parser.add_argument('-multi_proc', required=True)

args = parser.parse_args()

train_path = args.train_path
voca_out_path = args.voca_out_path
bpe_out_path = args.bpe_out_path
train_voca_threshold = int(args.train_voca_threshold)
final_voca_size = int(args.final_voca_size)
num_merges = int(args.num_merges)
multi_proc = int(args.multi_proc)

if multi_proc == -1:
	multi_proc = os.cpu_count()

if __name__ == '__main__':	
	
	# learn bpe from documents
	# learn_bpe 목적은 voca를 구하는것.
	learn_BPE.learn_bpe(
			path_list=train_path, 
			voca_out_path=voca_out_path, 
			space_symbol='</w>', 
			num_merges=num_merges, 
			voca_threshold=train_voca_threshold, 
			multi_proc=multi_proc
		)

	# bpe 적용하고 모든 bpe 단어 빈도수대로 추출 
		# 기존의 learn_BPE에서 생성된 voca의 freq와 다른 freq의 voca가 생성됨.(apply_BPE의 merge 방식이 learn_BPE의 merge_info 순서대로 하지 않기 때문임.)
	apply_BPE.apply_bpe(
			path_list=train_path, 
			out_list=bpe_out_path, 
			voca_path=voca_out_path, 
			new_voca_path=voca_out_path, 
			final_voca_threshold=1,
			space_symbol='</w>'
		)
	
	# 적용된 bpe 단어에서 빈도수대로 끊고 다시 적용 => reapply_bpe
		# apply_BPE 에서 사용된 merge로 부터 생성된 voca중에 freq가 낮은건 버리고, apply bpe 다시 적용. 여기서 생성되는 voca가 Final voca임. 앞으로 모두 이 voca 쓰면 됨.
	apply_BPE.apply_bpe(
			path_list=train_path, 
			out_list=bpe_out_path, 
			voca_path=voca_out_path, 
			new_voca_path=voca_out_path,
			final_voca_num=final_voca_size, 
			space_symbol='</w>'
		)