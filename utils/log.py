# -*- coding: utf-8 -*-

import utils

class PbIterator:
    def __init__(self, it, logger, name, every=10):
        self.it = iter(it)
        self.pbar = utils.Pbar(len(it))
        self.logger = logger
        self.name = name
        self.every = every

    def update(self):
        self.logger.update(**{self.name: str(self.pbar)})

    def __iter__(self):
        self.pbar.reset()
        self.update()
        return self

    def __next__(self):
        self.pbar.add(1)
        if self.pbar.count % self.every:
            self.update()
        return(next(self.it))

class LogManager:
    # What our display will look like
    dtxt = (
        '''
        Language: {lang}
        Run path: {run}
        ==========================
        Step: {step}
        Train Loss: {loss}
        Train Accuracy: {tacc}
        --------------------------
        Validation Loss: {vloss}
        Validation Accuracy: {acc}
        --------------------------
        * * * Only when testing final model * * *
        Test Loss: {tloss}
        Test Accuracy: {testacc}
        __________________________
        {msg}
        {pbar}
        '''
    )
    # Stuff we want to print even without a display
    # printable = ['lang', 'target', 'epoch', 'acc', 'msg']
    printable = ['lang', 'run', 'step', 'loss', 'tacc', 'vloss', 'acc', 'tloss', 'testacc']
    def __init__(self, display=False):
        if display:
            self.display = utils.Display(LogManager.dtxt)
        else:
            self.display = None

    def __enter__(self):
        if self.display:
            self.display.__enter__()
        return self

    def __exit__(self, *exc):
        if self.display:
            self.display.__exit__(*exc)
        return False

    def pbiter(self, it):
        if self.display:
            return PbIterator(it, self, 'pbar')
        else:
            return it

    def update(self, **kwargs):
        if self.display:
            self.display.update(**kwargs)
        else:
            for p in LogManager.printable:
                if p in kwargs:
                    print(f'{p}: {kwargs[p]}')
