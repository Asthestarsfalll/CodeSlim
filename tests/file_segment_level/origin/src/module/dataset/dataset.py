import torch
from torch.utils.data import DataLoader, Dataset


class RandomDataset(Dataset):
    def __init__(self, size=128, length=10):
        self.len = length
        self.data = torch.randn(length, 3, size, size)

    def __getitem__(self, index):
        return self.data[index]

    def __len__(self):
        return self.len


def get_dataloader(batch_size):
    train_dataset = RandomDataset()
    train_loader = DataLoader(
        dataset=train_dataset, batch_size=batch_size, shuffle=True
    )
    return train_loader

def get_testdataloader(batch_size):
    train_dataset = RandomDataset()
    train_loader = DataLoader(
        dataset=train_dataset, batch_size=batch_size, shuffle=True
    )
    return train_loader
