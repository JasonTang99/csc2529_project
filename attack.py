import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
import torchvision
from torchvision import transforms, models
from torchvision.datasets import MNIST, CIFAR10
from torchvision.transforms import InterpolationMode

import os
from tqdm import tqdm

from utils import create_resnet, calc_resize_shape, read_results, write_results
from models.gp_ensemble import GPEnsemble 
from parse_args import parse_args, post_process_args, process_args
from datasets import load_data

from cleverhans.torch.attacks.fast_gradient_method import fast_gradient_method
from cleverhans_fixed.projected_gradient_descent import (
    projected_gradient_descent,
)
from cleverhans_fixed.carlini_wagner_l2 import carlini_wagner_l2
# from cleverhans.torch.attacks.carlini_wagner_l2 import carlini_wagner_l2

def evaluate_attack(args, model, x, y, z):
    """
    Evaluate model on attacked data.
    """
    # load dataset
    test_loader = load_data(args, 0, train=False)

    # run evaluation
    model.eval()
    correct = 0
    l2_max, linf_max = 0, 0
    l2_count = 0
    # for images, labels in tqdm(test_loader):
    for images, labels in test_loader:
        images, labels = images.to(args.device), labels.to(args.device)

        if args.attack_method == 'baseline':
            pass
        elif args.attack_method == 'fgsm':
            adv_images = fast_gradient_method(
                model_fn=model,
                x=images,
                eps=args.epsilon,
                norm=args.norm,
                clip_min=0.0,
                clip_max=1.0,
            )
        elif args.attack_method == 'pgd':
            adv_images = projected_gradient_descent(
                model_fn=model,
                x=images,
                eps=args.epsilon,
                eps_iter=args.eps_iter,
                nb_iter=args.nb_iter,
                norm=args.norm,
                clip_min=0.0,
                clip_max=1.0,
                rand_init=args.rand_init,
                sanity_checks=False
            )
        elif args.attack_method == 'cw':
            adv_images = carlini_wagner_l2(
                model_fn=model,
                x=images,
                n_classes=args.num_classes,
                lr=x,
                binary_search_steps=y,
                max_iterations=z-100,
                initial_const=args.initial_const,
            )
            
        # Track the maximum L2 and Linf distances
        diff = (images - adv_images).view(images.shape[0], -1)
        l2 = torch.norm(diff, p=2, dim=1)
        linf = torch.norm(diff, p=float('inf'), dim=1)

        # l2_max = max(l2_max, l2)
        # linf_max = max(linf_max, linf)

        # linf_max = max(linf_max, torch.sum(torch.norm(diff, p=float('inf'), dim=1)))
    
        # l2_count += images.shape[0]

        print(l2)
        print(linf)
        # print("L2 max:", l2_max)
        # print("Linf max:", linf_max)

        outputs = model(adv_images)
        _, preds = torch.max(outputs, 1)
        correct += torch.sum(preds == labels.data).detach().cpu()

        # delete variables to save memory
        del images, labels, outputs, preds

        # TODO: delete
        print(correct)
        break
        # if l2_count >= 1024:
        #     break

    # test_acc = correct.double() / len(test_loader.dataset)
    # print(f'Test Accuracy on {args.attack_method}: {test_acc}')

    if args.attack_method == 'cw':
        return correct.double(), l2_max, linf_max #TODO test_acc
    return test_acc, 0, 0


if __name__ == "__main__":
    # parse args
    args = process_args(mode="attack")
    args.up_samplers = 0
    args.down_samplers = 0
    
    args.attack_method = "cw"
    args.batch_size = 8
    
    args = post_process_args(args, mode="attack")


    # set random seeds
    torch.manual_seed(0)

    # setup ensemble model
    model = GPEnsemble(args)

    # run attack
    # args.epsilon = 0.4
    # test_acc, _, _ = evaluate_attack(args, model, 0, 0, 0)
    # exit(0)
    # lr=x,
    # binary_search_steps=y,
    # max_iterations=z,
    # res = {}
    # fp="cw_results_0_0"
    # if os.path.exists(fp):
    #     res = read_results(fp)
    #     print("loaded {}".format(len(res)))
    for w in [1e-4, 1e-6, 1e-8, 1e-10, 1e-12]:
        for x in [0.5]:
            for y in [1, 2, 4, 6, 8, 10]:
                for z in [500]:
                    # if (w, x, y, z) in res:
                    #     continue
                    print("======================= w", w, "x", x, "y", y, "z", z)
                    args.initial_const = w
                    correct, l2, linf = evaluate_attack(args, model, x, y, z)
                    # res[(w, x, y, z)] = (correct, l2, linf)
                    # write_results(fp, res)



# 1e-7 0.5 5 100: 984 0.0655
# 1e-6 0.5 5 100: 587 0.9473
#   0.75 5 70: 357 1.9484
# 1e-5 0.5 5 100: 395 0.9260
#   0.75 5 70: 233 2.2975
# 1e-4 0.5 5 100: 75 tensor(1.4031)
#   0.75 5 70: 131 1.5001

# 1e-6: 191/1024 2.4079
# 1e-5 : 149/1024 2.3400 
#   (with 0.5 lr it gets 0.91 but 325/1024)
# 1e-4 1.0 5 50: 130/1024 1.6033
# 0.001 1.0 5 50: 40/1024 1.9224
# 0.01 1.0 5 50: 5/1024 2.0502 56 seconds
# 0.1 1.0 5 50: 6/1024 2.0107 56 seconds
# 1.0 1.0 5 50: 9/1024 2.7257 56 seconds

# 0.876953125 5e-2 1 600
# 0.849609375 1e-1 1 600
# 1.0 1 50: 0.1474609375 2.4272 (12 seconds)
# 1.0 1 200: 0.1474609375 2.4027 (47 seconds / 512)
# 1.0 1 400: 0.146484375 2.3819 
# 1.0 1 1000: 0.1484375 2.3436

# 1.0 5 25: 9/1024 2.1462 30 seconds
# 1.0 5 50: 5/1024 2.0502 56 seconds
# 1.0 3 50: 130/1024 1.6441 34 seconds
# 1.0 5 200: 5/1024 2.0226 3:39

# 1.0 10 25: 5/1024 2.1640 58 seconds
# 1.0 10 50: 5/1024 2.0833 1:50