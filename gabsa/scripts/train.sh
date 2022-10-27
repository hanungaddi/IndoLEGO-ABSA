#!/usr/bin/env bash

CUDA_VISIBLE_DEVICES=2,3 python main.py --do_train \
            --do_eval \
            --do_predict \
            --train_args /srv/nas_data1/text/randy/absa/facebook-absa/gabsa/train_args/train_args.json \
            --model_type t5 \
            --model_name_or_path Wikidepia/IndoT5-small \
            --max_len 256 \
            --task "aste" \
            --paradigm extraction \
            --prompt_path /srv/nas_data1/text/randy/absa/facebook-absa/gabsa/prompts/prompt.json \
            --prompt_option_path /srv/nas_data1/text/randy/absa/facebook-absa/gabsa/prompts/option.json \
            --pattern /srv/nas_data1/text/randy/absa/facebook-absa/gabsa/patterns/default.json \
            --dataset_name facebook_research \
            --data_dir /srv/nas_data1/text/randy/absa/facebook-absa/data/combination/prosa/gaste_format \
            --trains "train_news_annotator train_news_student train_socmed_HaloBCA train_socmed_Telmark train_socmed_V3_sentiment" \
            --devs "test_news" \
            --tests "test_news" \
            --blank_frac 1.0 \
            --random_state 42 \
            --output_dir /srv/nas_data1/text/randy/absa/models/facebook_research/generative_unprompted \
            --per_device_predict_batch_size 16
            # --trains "train_socmed_twenty_percent train_news_annotator train_news_student" \