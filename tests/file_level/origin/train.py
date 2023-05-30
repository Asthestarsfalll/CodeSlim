import torch
import torch.nn as nn
import torch.optim as optim
from src.model.resnet import ResNet18
from src.module.dataset.dataset import get_dataloader

num_epochs = 10
batch_size = 2
learning_rate = 0.001

train_loader = get_dataloader(batch_size)

model = ResNet18()

criterion = nn.CrossEntropyLoss()
optimizer = optim.Adam(model.parameters(), lr=learning_rate)

for epoch in range(num_epochs):
    running_loss = 0.0
    for i, inputs in enumerate(train_loader):
        inputs = inputs
        labels = torch.randint(low=0, high=10, size=(batch_size,))
        optimizer.zero_grad()
        outputs = model(inputs)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()
        running_loss += loss.item()
        if (i + 1) % 5 == 0:
            print(
                "Epoch [{}/{}], Step [{}/{}], Loss: {:.4f}".format(
                    epoch + 1, num_epochs, i + 1, len(train_loader), loss.item()
                )
            )
