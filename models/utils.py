import torch
import torch.nn as nn
from torchvision.models import resnet18, resnet34, resnet50, ResNet18_Weights, ResNet34_Weights, ResNet50_Weights


def calc_resize_shape(in_size, scaling_exp, scaling_factor=2):
    return int(in_size * (scaling_factor ** scaling_exp))

def create_resnet(arch="resnet18", num_classes=10, device="cpu", pretrained=True):
    """
    Create resnet model.
    """
    if arch == "resnet18":
        model = resnet18(weights=ResNet18_Weights.IMAGENET1K_V1 
                         if pretrained else None)
    elif arch == "resnet34":
        model = resnet34(weights=ResNet34_Weights.IMAGENET1K_V1
                         if pretrained else None)
    elif arch == "resnet50":
        model = resnet50(weights=ResNet50_Weights.IMAGENET1K_V1
                         if pretrained else None)
    else:
        raise ValueError("Model not supported.")
    
    # change output size
    model.fc = nn.Linear(model.fc.in_features, num_classes)

    # freeze all non-fc layers
    # for param in model.parameters():
    #     param.requires_grad = False
    # for param in model.fc.parameters():
    #     param.requires_grad = True
    
    # move model to device
    model = model.to(device)
    
    return model