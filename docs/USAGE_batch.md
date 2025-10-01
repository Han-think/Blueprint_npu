# USAGE (batch v3)
1) 편집: prompts/sys_template.txt, prompts/usr_template.txt, prompts/prompts_topics.txt
2) 모델 경로/리포: configs/models.txt 수정
3) 실행 예:
   .\.venv\Scripts\python.exe ai\cli\batch_dual_v3.py --ov_key phi4mini_ov --hf_key hf_small --topics prompts\prompts_topics.txt --jobs 1 --timeout_sec 90 --retries 0
4) 산출물:
   save/sessions/<stamp>_dual_batch_v3/{run.jsonl, run.md, run.qa.md, run.csv}
5) 검증:
   .\.venv\Scripts\python.exe tools\validate_outputs.py <run.jsonl>
