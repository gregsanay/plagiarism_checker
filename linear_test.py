try:
    import torch
    from torch import nn
except ImportError:
    import pytest
    pytest.skip("Skipping torch-dependent test: 'torch' package is not installed.", allow_module_level=True)

model = nn.Linear(1, 1)
x = torch.tensor([[1.0], [2.0], [3.0]])
y = torch.tensor([[2.0], [4.0], [6.0]])

criterion = nn.MSELoss()
optimizer = torch.optim.SGD(model.parameters(), lr=0.01)

for epoch in range(1000):
    pred = model(x)
    loss = criterion(pred, y)
    optimizer.zero_grad()
    loss.backward()
    optimizer.step()

print(model(torch.tensor([[4.0]])))
