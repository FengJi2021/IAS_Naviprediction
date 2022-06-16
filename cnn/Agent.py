from cnn import cnn_basic
import torch
from torchvision import datasets, transforms
from torch.utils.data import random_split
from torch.optim import Adam


INIT_LR = 1e-3
BATCH_SIZE = 64
EPOCHS = 10

TRAIN_SPLIT = 0.75
VAL_SPLIT = 1 - TRAIN_SPLIT

# load dataset
# data augmentation

#transform = transforms.Compose([transforms.Resize(255),
#                                transforms.CenterCrop(224),
#                                transforms.ToTensor()])

tr_data = datasets.ImageFolder('../dataset')
tr_data = torch.utils.data.DataLoader(tr_data, batch_size=BATCH_SIZE, shuffle=True)
numTrainSamples = int(len(tr_data) * TRAIN_SPLIT)
numValSamples = int(len(tr_data) * VAL_SPLIT)
trainData, valData = random_split(tr_data, [numTrainSamples, numValSamples], generator=torch.Generator().manual_seed(42))

model = cnn_basic(
    numChannel=3,
    fc2_dim=2
)
model.to(model.device)
opt = Adam(model.parameters(), lr=INIT_LR)

def training():
    for _ in range(0, EPOCHS):
        model.train()

        for batch, (X, y) in enumerate(tr_data):
            X, y = X.to(model.device), y.to(model.device)

            pred = model(X)
            loss = model.loss(pred, y)
            # Backpropagation
            opt.zero_grad()
            loss.backward()
            opt.step()

            loss, current = loss.item(), batch * len(X)
            print(f"loss: {loss:>7f}  [{current:>5d}/{size:>5d}]")

if __name__ == "__main__":
    training()
        







