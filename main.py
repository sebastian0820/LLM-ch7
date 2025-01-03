import json
import os
import tiktoken
from urllib import request
import torch
from torch.utils.data import DataLoader
from functools import partial
from dataset import InstructionDataset, format_input

def download_and_load_file(file_path, url):
    if not os.path.exists(file_path):
        with request.urlopen(url) as response:
            text_data = response.read().decode("utf-8")
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(text_data)
    else:
        with open(file_path, "r", encoding="utf-8") as file:
            text_data = file.read()
    with open(file_path, "r") as file:
        data = json.load(file)
    return data

file_path = "jjj.json"
url = (
    "https://raw.githubusercontent.com/rasbt/LLMs-from-scratch"
    "/main/ch07/01_main-chapter-code/instruction-data.json"
)
data = download_and_load_file(file_path, url)

# print("Number of entries:", len(data))
# print("Example entry:\n", data[50])

# model_input = format_input(data[999])
# desired_response = f"\n\n### Response:\n{data[999]['output']}"
# print(model_input + desired_response)

train_portion = int(len(data) * 0.85)
test_portion = int(len(data) * 0.1)
val_portion = len(data) - train_portion - test_portion
train_data = data[:train_portion]
test_data = data
val_data = data[train_portion + test_portion:]
# print("Training set length:", len(train_data))
# print("Test set length:", len(test_data))
# print("Validation set length:", len(val_data))

def custom_collate_fn(
    batch,
    pad_token_id = 50256,
    ignore_index = -100,
    allowed_max_length = None,
    device = "cpu"
):
    batch_max_length = max(len(item)+1 for item in batch)
    inputs_lst, targets_lst = [], []
    for item in batch:
        new_item = item.copy()
        new_item += [pad_token_id]

        padded = (new_item + [pad_token_id] * (batch_max_length - len(new_item)))
        inputs = torch.tensor(padded[:-1])
        targets = torch.tensor(padded[1:])

        mask = targets == pad_token_id
        indices = torch.nonzero(mask).squeeze()
        if indices.numel() > 1:
            targets[indices[1:]] = ignore_index

        if allowed_max_length is not None:
            inputs = inputs[:allowed_max_length]
            targets = targets[:allowed_max_length]

        inputs_lst.append(inputs)
        targets_lst.append(targets)

    inputs_tensor = torch.stack(inputs_lst).to(device)
    targets_tensor = torch.stack(targets_lst).to(device)
    return inputs_tensor, targets_tensor

tokenizer = tiktoken.get_encoding("gpt2")
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
torch.manual_seed(123)
num_workers = 0
batch_size = 8

customized_collate_fn = partial(
    custom_collate_fn,
    device = device,
    allowed_max_length = 1024
)

# train_dataset = InstructionDataset(train_data, tokenizer)
# train_loader = DataLoader(
#     train_dataset,
#     batch_size = batch_size,
#     collate_fn = customized_collate_fn,
#     shuffle = True,
#     drop_last = True,
#     num_workers = num_workers
# )
# val_dataset = InstructionDataset(val_data, tokenizer)
# val_loader = DataLoader(
#     val_dataset,
#     batch_size=batch_size,
#     collate_fn=customized_collate_fn,
#     shuffle=False,
#     drop_last=False,
#     num_workers=num_workers
# )
test_dataset = InstructionDataset(data, tokenizer)
test_loader = DataLoader(
    test_dataset,
    batch_size=batch_size,
    collate_fn=customized_collate_fn,
    shuffle=False,
    drop_last=False,
    num_workers=num_workers
)

# print("Train loader:")
# for inputs, targets in train_loader:
#     print(inputs.shape, targets.shape)

from gpt_download import download_and_load_gpt2
from Gpt.GPTModel import GPTModel
from chapter05 import load_weights_into_gpt
BASE_CONFIG = {
    "vocab_size": 50257, # Vocabulary size
    "context_length": 1024, # Context length
    "drop_rate": 0.0, # Dropout rate
    "qkv_bias": True # Query-key-value bias
}
model_configs = {
    "gpt2-small (124M)": {"emb_dim": 768, "n_layers": 12, "n_heads": 12},
    "gpt2-medium (355M)": {"emb_dim": 1024, "n_layers": 24, "n_heads": 16},
    "gpt2-large (774M)": {"emb_dim": 1280, "n_layers": 36, "n_heads": 20},
    "gpt2-xl (1558M)": {"emb_dim": 1600, "n_layers": 48, "n_heads": 25},
}
CHOOSE_MODEL = "gpt2-small (124M)"
BASE_CONFIG.update(model_configs[CHOOSE_MODEL])
model_size = CHOOSE_MODEL.split(" ")[-1].lstrip("(").rstrip(")")
# settings, params = download_and_load_gpt2(
#     model_size=model_size,
#     models_dir="gpt2"
# )

model = GPTModel(BASE_CONFIG)
# load_weights_into_gpt(model, params)
import re
file_name = f"{re.sub(r'[ ()]', '', CHOOSE_MODEL) }-sft.pth"
model.load_state_dict(torch.load(file_name))
print(f"Model loaded from {file_name}")

model.eval()

from chapter05 import generate, text_to_token_ids, token_ids_to_text, calc_loss_loader, train_model_simple

# input_text = format_input(val_data[0])
# token_ids = generate(
#     model=model,
#     idx=text_to_token_ids(input_text, tokenizer),
#     max_new_tokens=35,
#     context_size=BASE_CONFIG["context_length"],
#     eos_id=50256,
# )
# generated_text = token_ids_to_text(token_ids, tokenizer)
# response_text = generated_text[len(input_text):].strip()
# print(response_text)

# model.to(device)
# with torch.no_grad(): 
#     train_loss = calc_loss_loader( train_loader, model, device, num_batches=5 ) 
#     val_loss = calc_loss_loader( val_loader, model, device, num_batches=5 )
# print("Training loss:", train_loss) 
# print("Validation loss:", val_loss)

# import time
# start_time = time.time()
# torch.manual_seed(123)
# optimizer = torch.optim.AdamW(model.parameters(), lr=0.00005, weight_decay=0.1)
# num_epochs = 2
# train_losses, val_losses, tokens_seen = train_model_simple(model, train_loader, val_loader, optimizer, device,
#                                                             num_epochs=num_epochs, eval_freq=5, eval_iter=5,
#                                                             start_context=format_input(val_data[0]), tokenizer=tokenizer)
# end_time = time.time()
# execution_time_minutes = (end_time - start_time) / 60
# print(f"Training completed in {execution_time_minutes:.2f} minutes.")

# from chapter05 import plot_losses
# epochs_tensor = torch.linspace(0, num_epochs, len(train_losses))
# plot_losses(epochs_tensor, tokens_seen, train_losses, val_losses)

for entry in data:
    input_text = format_input(entry)
    token_ids = generate(
        model=model,
        idx=text_to_token_ids(input_text, tokenizer).to(device),
        max_new_tokens=256,
        context_size=BASE_CONFIG["context_length"],
        eos_id=50256
    )
    generated_text = token_ids_to_text(token_ids, tokenizer)
    response_text = (
        generated_text[len(input_text):]
        .replace("### Response:", "")
        .strip()
    )
    with open("results.txt", "a", encoding="utf-8") as file:
        file.write(input_text)
        file.write(f"\nCorrect response:\n>> {entry['output']}")
        file.write(f"\nModel response:\n>> {response_text.strip()}")
        file.write("\n-------------------------------------\n")
print("Results saved to results.txt")
# file_name = f"{re.sub(r'[ ()]', '', CHOOSE_MODEL) }-sft.pth"
# torch.save(model.state_dict(), file_name)
# print(f"Model saved as {file_name}")