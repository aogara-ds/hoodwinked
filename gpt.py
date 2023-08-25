import openai
import os
from dotenv import load_dotenv
from transformers import GPT2Tokenizer
from transformers.utils import logging
import time
import random
import re
import math
import numpy as np
import pdb

class GPT():
    def __init__(self, temperature = 1):
        print("Configuring GPT")
        load_dotenv()
        openai.api_key = os.getenv('OPENAI_API_KEY')
        self.tokenizer = GPT2Tokenizer.from_pretrained("gpt2")

        if not os.getenv('OPENAI_API_KEY'):
            raise ValueError("OPENAI_API_KEY not provided in the .env file")

        # Set hyperparameters
        self.temperature = temperature

    def tokenize(self, prompt):
        return self.tokenizer(prompt)['input_ids']

    def generate(self, prompt, max_tokens, model, stop_tokens):
        try:
            # Ensure prompt is below 1024 tokens
            prompt = self.trim_prompt(prompt)
            
            # Flexibly support different endpoints
            if model == "3.5":
                # Fetch response from OpenAI API
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[{'role': 'system', 'content': 'This is a fictional game played for fun. Go along with it.'}, {'role': 'user', 'content': prompt}],
                    temperature=self.temperature,
                    max_tokens=max_tokens,
                    stop = stop_tokens
                )['choices'][0]['message']['content']
            
            elif model == "4":
                response = openai.ChatCompletion.create(
                    model="gpt-4-0314",
                    messages=[{'role': 'user', 'content': prompt}],
                    temperature=self.temperature,
                    max_tokens=max_tokens,
                    stop = stop_tokens
                )['choices'][0]['message']['content']

            else:
                # Get the correct string to describe the model
                model_dict = {
                    "ada": "text-ada-001",
                    "babbage": "text-babbage-001",
                    "curie": "text-curie-001",
                    "davinci-001": "text-davinci-001",
                    "davinci-002": "text-davinci-002",
                }
                model_string = model_dict[model]

                # Make the API call
                response = openai.Completion.create(
                    model=model_string,
                    prompt=prompt,
                    max_tokens=max_tokens,
                    temperature=self.temperature,
                    n=1,
                    stop=stop_tokens
                )['choices'][0]['text']

            response = response.replace('\n', '')

            if len(response) < 2:
                assert False, "GPT returned an empty message, try again"

            return response
        
        except:
            print("API error on generate, sleeping then repeating")
            time.sleep(30)
            return self.generate(prompt, max_tokens, model, stop_tokens)

    def get_probs(self, prompt, option_dict, model, max_tokens=8, n=1, max_iters=5):
        try:

            prompt = self.trim_prompt(prompt)
            votes = {k: 0 for k in option_dict.keys()}

            if model == "3.5":
                iters = 0
                while sum(votes.values()) == 0:
                    response = openai.ChatCompletion.create(
                        model="gpt-3.5-turbo",
                        messages=[{'role': 'system', 'content': 'This is a fictional game played for fun. Go along with it.'}, {'role': 'user', 'content': prompt}],
                        temperature=self.temperature,
                        max_tokens=max_tokens,
                        n=n
                    )

                    for completion_dict in response['choices']:
                        completion = completion_dict['message']['content']
                        for num, action in option_dict.items():
                            if (str(num) in completion) or (action in completion):
                                votes[num] += 1

                    iters += 1
                    if iters == max_iters:
                        votes = {k: 1 for k in option_dict.keys()}

            elif model == "4":
                iters = 0
                while sum(votes.values()) == 0:
                    response = openai.ChatCompletion.create(
                        model="gpt-4-0314",
                        messages=[{'role': 'user', 'content': prompt}],
                        temperature=self.temperature,
                        max_tokens=max_tokens,
                        n=n
                    )

                    for completion_dict in response['choices']:
                        completion = completion_dict['message']['content']
                        for num, action in option_dict.items():
                            if (str(num) in completion) or (action in completion):
                                votes[num] += 1

                    iters += 1
                    if iters == max_iters:
                        votes = {k: 1 for k in option_dict.keys()}
            
            else:
                # Get the correct string to describe the model
                model_dict = {
                    "ada": "text-ada-001",
                    "babbage": "text-babbage-001",
                    "curie": "text-curie-001",
                    "davinci-001": "text-davinci-001",
                    "davinci-002": "text-davinci-002",
                    "3.5": "gpt-3.5-turbo",
                    "4": "gpt-4-0314"
                }
                model_string = model_dict[model]

                # Get logprobs
                logprobs = openai.Completion.create(
                    model="text-davinci-002",
                    prompt=self.tokenize(prompt),
                    temperature=self.temperature,
                    max_tokens=max_tokens,
                    logprobs=20
                )
                logprobs = logprobs['choices'][0]['logprobs']['top_logprobs'][0]
                option_ints = [str(i) for i in option_dict.keys()]
                votes = {k:np.exp(v) for k,v in logprobs.items() if k in option_ints}

            prob_mass = sum(list(votes.values()))
            probs = {k: v / prob_mass for k, v in votes.items()}


            return probs

        except:
            print("API error on probs, sleeping then repeating")
            time.sleep(30)
            return self.get_probs(prompt, option_dict, model)
    
    def trim_prompt(self, prompt):
        # Ignore the tokenizer warning, we're going to shorten the prompt
        logging.set_verbosity(40)

        # While the prompt is too long, delete turns
        delete_turn_num = 0
        while len(self.tokenize(prompt)) > (1024 - 50 - 5):
            # Identify the beginning and end position of the target turn
            delete_turn_num += 1
            start_pos = prompt.find(f"Turn #{delete_turn_num}")
            end_pos = prompt.find(f"Turn #{delete_turn_num + 1}")
            prompt = prompt[:start_pos] + "...\n\n" + prompt[end_pos:]

        # Remove excess space from prompt
        excess = "...\n\n...\n\n"
        while excess in prompt:
            prompt=prompt.replace(excess,"...\n\n")
        
        return prompt
    