from data_utils import ABSADataset, NonABSADataset, Pattern, Prompter
from model import ABSAGenerativeModelWrapper
from training import ABSAGenerativeTrainer
import pandas as pd
from datasets import Dataset
import torch
from typing import Dict, Any

from argparse import ArgumentParser

import json

import os

def init_args() -> Dict[str,Any]:
    parser = ArgumentParser()

    parser.add_argument("--train_seed",type=int,help="Training seed",required=False)
    parser.add_argument("--n_gpu",type=str,help="Gpu device(s) used",default='0')

    parser.add_argument("--do_train",action="store_true",help="Do training")
    parser.add_argument("--do_eval",action="store_true",help="Do calidation phase.")
    parser.add_argument("--do_predict",action="store_true",help="Do prediction")

    parser.add_argument("--model_config",type=str,help="Path to model configuration json file.",default="configs/model_config.json")
    parser.add_argument("--data_config",type=str,help="Path to data configuration json file.",default="configs/data_config.json")
    parser.add_argument("--pattern_config",type=str,help="Path to pattern configuration json file.",default="configs/pattern_config.json")
    parser.add_argument("--prompt_config",type=str,help="Path to prompter configuration json file.",default="configs/prompt_config.json")
    parser.add_argument("--train_args",type=str,help="Path to train configuration json file.",default="configs/train_args.json")
    parser.add_argument("--encoding_args",type=str,help="Path to encoding configuration json file.",default="configs/encoding_args.json")
    parser.add_argument("--decoding_args",type=str,help="Path to decoding configuration json file.",default="configs/decoding_args.json")
    
    parser.add_argument("--patience",type=int,help="Early stopping patience, if -1 then no early stopping.",default=-1)

    args = parser.parse_args()
    args.model_config = json.load(open(args.model_config,'r'))
    args.data_config = json.load(open(args.data_config,'r'))
    args.pattern_config = json.load(open(args.pattern_config,'r'))
    args.prompt_config = json.load(open(args.prompt_config,'r'))
    args.train_args = json.load(open(args.train_args,'r'))
    args.encoding_args = json.load(open(args.encoding_args,'r'))
    args.decoding_args = json.load(open(args.decoding_args,'r'))

    return args

def main():
    args = init_args()
    os.environ["CUDA_VISIBLE_DEVICES"] = args.n_gpu

    print("Initializing...")
    wrapper = ABSAGenerativeModelWrapper(**args.model_config)
    pattern = Pattern(**args.pattern_config)
    prompter = Prompter(**args.prompt_config)
    trainer = ABSAGenerativeTrainer(absa_model_and_tokenizer=wrapper,pattern=pattern,do_train=args.do_train,do_eval=args.do_eval,early_stopping_patience=args.patience)

    print("Prepare datasets...")
    # ABSA Datasets
    if args.do_train:
        train_absa_args = args.data_config["train"]["absa"].copy()
        train_absa_args.update({
            "prompter" : prompter,
            "pattern" : pattern
        })
        train_absa = ABSADataset(**train_absa_args)

        non_absa_train = []
        for non_absa_args in args.data_config["train"]["non_absa"]:
            non_absa_train.append(NonABSADataset(**non_absa_args))
        
        absa_builder_args = args.data_config["train"]["absa_builder_args"]
        train_data = pd.concat([non_absa_ds.build_data().to_pandas() for non_absa_ds in non_absa_train] + [train_absa.build_train_val_data(**absa_builder_args).to_pandas()])
        train_data = Dataset.from_pandas(train_data)
        val_data = None
    
    if args.do_eval:
        val_absa_args = args.data_config["val"]["absa"].copy()
        val_absa_args.update({
            "prompter" : prompter,
            "pattern" : pattern
        })
        val_absa = ABSADataset(**val_absa_args)

        non_absa_val = []
        for non_absa_args in args.data_config["val"]["non_absa"]:
            non_absa_val.append(NonABSADataset(**non_absa_args))
        
        val_data = pd.concat([non_absa_ds.build_data().to_pandas() for non_absa_ds in non_absa_val] + [val_absa.build_train_val_data(**args.data_config["val"]["absa_builder_args"]).to_pandas()])
        val_data = Dataset.from_pandas(val_data)
    
    if args.do_train:
        print("Training phase...")
        trainer.prepare_data(train_dataset=train_data,eval_dataset=val_data, **args.encoding_args)
        trainer.compile_train_args(train_args_dict=args.train_args)
        trainer.prepare_trainer(args.decoding_args)
        trainer.train(output_dir=args.train_args["output_dir"],random_seed=args.train_seed)
    
    if args.do_predict:
        print("Prediction phase...")
        test_absa_args = args.data_config["test"]["absa"].copy()
        test_absa_args.update({
            "prompter" : prompter,
            "pattern" : pattern
        })
        test_absa = ABSADataset(**test_absa_args)

        non_absa_test = []
        for non_absa_args in args.data_config["test"]["non_absa"]:
            non_absa_test.append(NonABSADataset(**non_absa_args))

        device = torch.device("cuda:0") if torch.cuda.is_available() else torch.device("cpu")
        
        non_absa_preds = trainer.predict_non_absa(dataset=non_absa_test,device=device,encoding_args=args.encoding_args,decoding_args=args.decoding_args)
        absa_preds, summary_score, absa_str_preds = trainer.predict_absa(dataset=test_absa,task_tree=args.data_config["test"]["absa_builder_args"]["task_tree"],
                                                                         device=device,encoding_args=args.encoding_args,decoding_args=args.decoding_args,max_len=args.encoding_args["max_length"],
                                                                         i_pattern=args.data_config["test"]["absa_builder_args"]["i_pattern"])

        # Save the result for error analysis
        print("Save results...")
        output_dir = args.train_args["output_dir"]
        # Non ABSA
        try:
            non_absa_result = [ds.build_data().to_pandas() for ds in non_absa_test]
            non_absa_result = pd.concat(non_absa_result,axis=0)
            non_absa_result["prediction"] = non_absa_preds
            non_absa_result.to_csv(os.path.join(output_dir,"non_absa_pred.csv"),index=False)
        except:
            pass

        # ABSA
        all_absa_result = []
        for task in args.data_config["test"]["absa_builder_args"]["task_tree"]:
            blank_incomplete_targets = [[] for n in range(len(test_absa))]
            absa_result = test_absa.build_test_data(task,"extraction",blank_incomplete_targets,args.data_config["test"]["absa_builder_args"]["i_pattern"]).to_pandas()
            absa_result["prediction"] = absa_preds[task]
            # absa_result["string_prediction"] = absa_string_preds[task]
            all_absa_result.append(absa_result)
        all_absa_result = pd.concat(all_absa_result)
        all_absa_result.to_csv(os.path.join(output_dir,"absa_pred.csv"),index=False)
        absa_str_preds.to_csv(os.path.join(output_dir,"absa_str_pred.csv"),index=False)

        print("Prediction result:")
        print(summary_score)

        # Summary score
        json.dump(summary_score,open(os.path.join(output_dir,"absa_score.json"),'w'))

    # Save arguments
    json.dump(vars(args),open(os.path.join(output_dir,"args.json"),'w'))

if __name__ == "__main__":
    main()