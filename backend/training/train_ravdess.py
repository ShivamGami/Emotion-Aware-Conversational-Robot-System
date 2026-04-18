import os
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import librosa
import numpy as np
import zipfile

# 1. Provide instructions to the user to place data
print("=== RAVDESS PyTorch Training Script ===")
print("Please ensure you have the RAVDESS dataset downloaded.")
print("You can download the 'Audio_Speech_Actors_01-24' zipped folder from Kaggle:")
print("Link: https://www.kaggle.com/datasets/uwrfkaggler/ravdess-emotional-speech-audio")
print("Place the ZIP file or the extracted 'Audio_Speech_Actors_01-24' folder in the 'data' directory here.")

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)

# Helper to automatically extract if zip is there
zip_files = [f for f in os.listdir(DATA_DIR) if f.endswith(".zip")]
extract_path = os.path.join(DATA_DIR, "Audio_Speech_Actors_01-24")

for zip_file in zip_files:
    zip_path = os.path.join(DATA_DIR, zip_file)
    if not os.path.exists(extract_path):
        print(f"Found ZIP file {zip_file}. Extracting...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(DATA_DIR)

class RavdessDataset(Dataset):
    def __init__(self, root_dir):
        self.file_paths = []
        self.labels = []
        
        if not os.path.exists(root_dir):
            print(f"Warning: Data directory {root_dir} not found. Dataset will be empty.")
            return

        for actor_dir in os.listdir(root_dir):
            actor_path = os.path.join(root_dir, actor_dir)
            if os.path.isdir(actor_path):
                for file_name in os.listdir(actor_path):
                    if file_name.endswith('.wav'):
                        # RAVDESS naming format: 03-01-06-01-02-01-12.wav
                        # Emotion is the 3rd part (index 2)
                        parts = file_name.split('-')
                        if len(parts) >= 3:
                            emotion_label = int(parts[2]) - 1 # 0-indexed (0 to 7)
                            self.file_paths.append(os.path.join(actor_path, file_name))
                            self.labels.append(emotion_label)

    def __len__(self):
        return len(self.file_paths)

    def __getitem__(self, idx):
        path = self.file_paths[idx]
        label = self.labels[idx]
        
        # Load audio and extract MFCC
        data, sr = librosa.load(path, sr=22050, mono=True, duration=3, offset=0.5)
        mfccs = librosa.feature.mfcc(y=data, sr=sr, n_mfcc=40)
        mfccs_mean = np.mean(mfccs.T, axis=0) # shape: (40,)
        
        # We need shape (1, 40) for the 1D CNN
        tensor_data = torch.tensor(mfccs_mean, dtype=torch.float32).unsqueeze(0)
        tensor_label = torch.tensor(label, dtype=torch.long)
        return tensor_data, tensor_label

class AudioEmotionCNN(nn.Module):
    def __init__(self):
        super(AudioEmotionCNN, self).__init__()
        self.conv1 = nn.Conv1d(1, 64, kernel_size=3, padding=1)
        self.relu = nn.ReLU()
        self.maxpool = nn.MaxPool1d(kernel_size=2)
        self.fc1 = nn.Linear(64 * 20, 128)
        self.fc2 = nn.Linear(128, 8) 

    def forward(self, x):
        x = self.conv1(x)
        x = self.relu(x)
        x = self.maxpool(x)
        x = x.view(x.size(0), -1)
        x = self.fc1(x)
        x = self.relu(x)
        x = self.fc2(x)
        return x

def train():
    dataset = RavdessDataset(extract_path)
    if len(dataset) == 0:
        print("No training data found. Please add the RAVDESS audio dataset to train.")
        return
        
    dataloader = DataLoader(dataset, batch_size=32, shuffle=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = AudioEmotionCNN().to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=0.001)

    epochs = 50
    print(f"Starting Training for {epochs} epochs on device: {device}...")
    for epoch in range(epochs):
        running_loss = 0.0
        correct = 0
        total = 0
        for inputs, labels in dataloader:
            inputs, labels = inputs.to(device), labels.to(device)
            optimizer.zero_grad()
            
            outputs = model(inputs)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            
            running_loss += loss.item()
            _, predicted = torch.max(outputs.data, 1)
            total += labels.size(0)
            correct += (predicted == labels).sum().item()
            
        epoch_loss = running_loss / len(dataloader)
        epoch_acc = 100 * correct / total
        print(f"Epoch [{epoch+1}/{epochs}] Loss: {epoch_loss:.4f} Acc: {epoch_acc:.2f}%")

    model_save_path = os.path.join(os.path.dirname(__file__), "..", "voice_model.pth")
    torch.save(model.state_dict(), model_save_path)
    print(f"Real Model saved to {model_save_path}")

if __name__ == "__main__":
    train()
