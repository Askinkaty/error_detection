# -*- coding: utf-8 -*-

import os

import torch
import petname

from . import model

from . import (
    cfg,
    dataset,
    pipeline
)

class Trainer:
    def __init__(self, args):
        self.pl = pipeline.InputPipeline()
        self.device = model.get_device(args.force_cpu)
        self.train_dl, self.test_dl = self.pl.get_dataloaders(
            batch_size=args.batch_size,
            num_workers=os.cpu_count() // 2,
            pin_memory=True
        )
        self.model = model.Model(
            self.pl.vectors.dim,
            args.hidden_units,
            args.output_units,
            args.lstm_layers,
            args.dropout,
            int(cfg.window_rad),
            #dataset.get_vocab_len()
        ).to(self.device)
        self.optimizer = torch.optim.Adam(self.model.parameters())
        self.global_step = 0
        self.epochs = args.epochs
        self.max_acc = 0
        if hasattr(args, 'run_path'):
            self.run_dir = os.path.join(cfg.run_dir, args.run_path)
            # TODO load latest instead
            self.load('best')
        else:
            self.run_dir = self.new_run_dir(cfg.run_dir)

    def new_run_dir(self, base_dir):
        cond = True
        while cond:
            rname = petname.generate(letters=8)
            run_dir = os.path.join(base_dir, rname)
            cond = os.path.isdir(run_dir)
        os.makedirs(run_dir)
        print('Saving run data in', run_dir)
        return run_dir

    # TODO graceful shutdown, saving state
    def train(self, logger):
        self.logger = logger
        self.logger.update(
            lang=cfg.lang,
            target=cfg.target,
            run=os.path.basename(self.run_dir)
        )
        #criterion = torch.nn.CrossEntropyLoss()
        criterion = torch.nn.BCEWithLogitsLoss()
        self.model.train()
        self.logger.update(msg='Training...')
        for e in range(self.epochs):
            self.logger.update(epoch=f'{e+1} / {self.epochs}')
            closs = 0
            for i, (windows, labels) in enumerate(
                self.logger.pbiter(self.train_dl)
            ):
                self.global_step += 1
                self.optimizer.zero_grad()
                output = self.model.forward(windows.to(self.device))
                loss = criterion(output, labels.to(self.device))
                closs += loss.data.item()
                loss.backward()
                self.optimizer.step()
                if i % 10 == 0:
                    self.logger.update(
                        step=i,
                        loss=loss
                    )
                # TODO config somewhere?
                if i % 999 == 0:
                    self.test()
                    self.model.train()
                    self.logger.update(msg='Training...')
            closs /= i

    def test(self):
        cacc = 0
        self.model.eval()
        self.logger.update(
            msg='Evaluating...'
        )
        # all_labels = torch.empty(0, dtype=torch.int64).to(self.device)
        # all_preds = torch.empty(0, dtype=torch.int64).to(self.device)
        # all_conf = torch.empty(0, dtype=torch.float32).to(self.device)
        for i, (windows, labels) in enumerate(
            self.logger.pbiter(self.test_dl)
        ):
            labels = labels.to(self.device)
            output = self.model.forward(windows.to(self.device))
            preds = torch.argmax(output, dim=1)
            # probs = torch.nn.functional.softmax(output, dim=1)
            # conf = torch.gather(probs, 1, preds.unsqueeze(1)).squeeze()
            # all_labels = torch.cat((all_labels, labels), 0)
            # all_preds = torch.cat((all_preds, preds), 0)
            # all_conf = torch.cat((all_conf, conf), 0)
            acc = torch.mean((preds == labels).float())
            cacc += acc.data.item()
        cacc /= i
        if cacc > self.max_acc:
            self.max_acc = cacc
            self.logger.update(
                macc=f'{cacc:.2%}',
                msg='Saving model...'
            )
            self.save('best')
            # np.save(
            #     os.path.join(self.run_dir, 'labels.npy'),
            #     all_labels.cpu().detach().numpy()
            # )
            # np.save(
            #     os.path.join(self.run_dir, 'predictions.npy'),
            #     all_preds.cpu().detach().numpy()
            # )
            # np.save(
            #     os.path.join(self.run_dir, 'confidence.npy'),
            #     all_conf.cpu().detach().numpy()
            # )
        self.logger.update(acc=f'{cacc:.2%}')

    def save(self, name):
        torch.save(
            {
                'global_step': self.global_step,
                'model': self.model.state_dict(),
                'optimizer': self.optimizer.state_dict()
            },
            os.path.join(self.run_dir, f'{name}.pt')
        )

    def load(self, name):
        ckp = torch.load(os.path.join(self.run_dir, f'{name}.pt'))
        self.model.load_state_dict(ckp['model'])
        self.optimizer.load_state_dict(ckp['optimizer'])
        self.global_step = ckp['global_step']
