from datasets import Dataset, DatasetDict
from pattern import Pattern
from prompt import Prompter
import pandas as pd

from typing import Dict, List

from constant import SEP, SENTTAG2WORD, SENTIMENT_ELEMENT

# THINGS TO DO
# a. Consider tasks
# b. Consider prompter
# c. Consider random shuffle
# d. Consider extraction & imputation
# e. Multiply the data or not

sample = "It rarely works and when it does it 's incredibly slow .####[([2], [1], 'NEG')]"

class ABSADataset(Dataset):
    """
    ABSA Dataset.
    """
    def __init__(self,data_path:str,target_format:str="acos",tasks:Dict={"extraction" : ["ao","ac","as"],"imputation" : {"acos" : ["ao","ac","aos"]}},prompter:Prompter=Prompter(),pattern:Pattern=Pattern(),multiply:bool=True,shuffle:bool=True,random_state:int=None):
        """
        ### DESC
            Constructor method for ABSA dataset.
        ### PARAMS
        * data_path: Path to ABSA txt dataset.
        * target_format: Format of the targets in the dataset file. Example: ao, aosc, aos, etc.
        * tasks: Dictionary for available tasks. Available keys are 'extraction' and 'imputation'. Task names indicates the sentiment elements to be extracted, available sentiment elements are Aspect Term (a or A), Opinion Term (o or O), Sentiment (s or S), and Category (c or C). Example of task name: aoc, aos, aosc, ao, etc.
        * prompter: Prompter object to add prompt.
        * pattern: Pattern object.
        * multiply: Multiply the dataset (True) or randomly assign random task to the data (uniform distribution).
        * shuffle: Shuffle the dataset.
        * random_state: Seed for randomize the shuffle (only works when shuffle equals True).
        """
        super().__init__()
        # Assert data type
        assert isinstance(data_path,str) and isinstance(target_format,str) \
            and isinstance(tasks,dict) and isinstance(multiply,bool) \
            and isinstance(multiply,bool) and isinstance(shuffle,bool) \
            and isinstance(random_state,int)

        # Assert key of tasks
        tasks_key = set(tasks.keys())
        assert tasks_key.issubset({"extraction", "imputation"})

        # Read the data
        data = self.read_data(data_path)
        
        # Is multiply or not
        new_data = []
        categories = []
        if multiply:
            for row in data:
                text, num_targets = row["text"], row["num_targets"]
                original_targets = self.process_num_targets(text,num_targets,task=target_format)
                
                # Record categories for category related tasks.
                for target in original_targets:
                    if "category" in target.keys():
                        if target["category"] not in categories:
                            categories.append(target["category"])
                
                # Multiply
                for task in tasks["extraction"]:
                    target = self.reduce_target(original_targets,task)
                    new_data_entry = {
                        "text" : text,
                        "paradigm" : "extraction",
                        "task" : task,
                        "target" : target
                    }
                    new_data.append(new_data_entry)
                for task_list in tasks["imputation"]:
                    pass
    
    def process_num_targets(self,text:str,num_targets:List[tuple],task:str) -> List[Dict]:
        """
        ### DESC
            Method for processing num targets to target in the format list of dictionaries.
        ### PARAMS
        * text: Text source.
        * num_targets: Targets in the form list of tuples, may consist of aspect term or opinion term indexes.
        * task: The designated task. Example: axos, aos, ac, ao, etc.
        ### RETURN
        * result_targets: The resultant targets in the form list of dictionaries.
        """
        splitted_text = text.split()
        result_targets = []
        for num_target in num_targets:
            assert len(num_target) == len(task) # number of element in the num targets must be the same with the task
            target = {}
            for i, se in enumerate(task): # iterate a, c, o, s
                assert se in 'acos'
                key = SENTIMENT_ELEMENT[se]
                if se == 'a' or se == 'o':
                    value = ' '.join([splitted_text[j] for j in num_target[i]])
                elif se == 's':
                    value = SENTTAG2WORD[num_target[i]]
                else: # se == 'c
                    value = num_target[i]
                target[key] = value
            result_targets.append(target)
        return result_targets
    
    def read_data(self,path:str) -> List[Dict]:
        f""""
        ### DESC
            Method to read dataset. Each line is in the format of TEXT{SEP}TARGETS .
        ### PARAMS
        * path: Data path.
        ### RETURN
        * data: List of dictionaries.
        """
        assert path.endswith(".txt")
        with open(path,'r') as reader:
            data = reader.read().strip().splitlines()
        for i,line in enumerate(data):
            try:
                text, num_targets = line.split(SEP)
                num_targets = eval(num_targets)
            except Exception as e:
                raise ValueError(f"Each line should be in the format 'TEXT{SEP}TARGET'. Example: {sample}")
            data[i] = {"text" : text, "num_targets" : num_targets}
        return data
    
    def reduce_target(self,target:Dict[str,str],task:str="ao") -> Dict[str,str]:
        """
        ### DESC
            Method to reduce sentiment elements in the designated targets.
        ### PARAMS
        * target: An ABSA target containing sentiment elements.
        * task: The task related to the resulting target.
        ### RETURN
        * result_target: The resultant target.
        """
        result_target = target.copy()
        for se in "acos":
            key = SENTIMENT_ELEMENT[se]
            if se not in task and key in result_target:
                del result_target[key]
        return result_target


if __name__ == "__main__":
    a = ABSADataset('test.txt',{'imputation' : ['ao']})
    ABSADataset