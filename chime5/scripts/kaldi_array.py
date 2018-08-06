import os
import stat
from pathlib import Path
from shutil import copytree, copyfile

import sacred

from chime5.scripts.create_mapping_json import Chime5KaldiIdMapping
from chime5.scripts.kaldi import ORG_DIR
from nt.database.chime5 import Chime5
from nt.io.file_handling import mkdir_p
from nt.utils.process_caller import run_process

ex = sacred.Experiment('Kaldi array')
db = Chime5('/net/vol/jenkins/jsons/chime5_orig.json')

NEEDED_FILES = ['cmd.sh', 'path.sh', 'get_model.bash']
NEEDED_DIRS = ['data/lang', 'data/local', 'data/srilm', 'conf', 'local']


def get_files(base_dir, train_set, dev_set, org_dir=ORG_DIR):
    if not (base_dir / 'data' / train_set).exists():
        copytree(str(org_dir / 'data' / train_set),
                 str(base_dir / 'data' / train_set))
    if not (base_dir / 'data' / dev_set).exists():
        copytree(str(org_dir / 'data' / dev_set),
                 str(base_dir / 'data' / dev_set))
    if not (base_dir / 'get_array_model.bash').exists():
        file = str(base_dir / 'get_array_model.bash')
        copyfile(str(org_dir / 'get_array_model.bash'), file)
        st = os.stat(file)
        os.chmod(file, st.st_mode | stat.S_IEXEC)


def calculate_mfccs(base_dir, dataset, num_jobs=20, config='mfcc.conf',
                    recalc=False):
    '''

    :param base_dir: kaldi egs directory with steps and utils dir
    :param dataset: name of folder in data
    :param num_jobs: number of parallel jobs
    :param config: mfcc config
    :param recalc: recalc feats if already calculated
    :return:
    '''
    if isinstance(dataset, str):
        dataset = base_dir / 'data' / dataset
    assert dataset.exists()
    if not (dataset / 'feats.scp').exists() or recalc:
        run_process([
            f'{base_dir}/steps/make_mfcc.sh', '--nj', str(num_jobs),
            '--mfcc-config', f'{base_dir}/conf/{config}',
            '--cmd', 'run.pl', f'{dataset}',
            f'{dataset}/make_mfcc', f'{dataset}/mfcc'],
            cwd=str(base_dir), stdout=None, stderr=None
        )

    if not (dataset / 'cmvn.scp').exists() or recalc:
        run_process([
            f'{base_dir}/steps/compute_cmvn_stats.sh',
            f'{dataset}', f'{dataset}/make_mfcc', f'{dataset}/mfcc'],
            cwd=str(base_dir), stdout=None, stderr=None
        )
    run_process([
        f'{base_dir}/utils/fix_data_dir.sh', f'{dataset}'],
        cwd=str(base_dir), stdout=None, stderr=None
    )


def calculate_ivectors(ivector_dir, base_dir, train_affix, dataset_dir,
                       extractor_dir, num_jobs=8):
    '''
    
    :param ivector_dir: ivector directory may be a string, bool or Path
    :param base_dir: kaldi egs directory with steps and utils dir
    :param train_affix: dataset specifier (dataset name without train or dev)
    :param dataset_dir: kaldi dataset dir
    :param extractor_dir: directory of the ivector extractor (may be None)
    :param num_jobs: number of parallel jobs
    :return: 
    '''
    if isinstance(ivector_dir, str):
        ivector_dir = base_dir / 'exp' / ('nnet3_' + train_affix) / ivector_dir
    elif isinstance(ivector_dir, bool):
        ivector_dir = base_dir / 'exp' / ('nnet3_' + train_affix) / (
            'ivectors_' + dataset_dir.name)
    elif isinstance(ivector_dir, Path):
        ivector_dir = ivector_dir
    else:
        raise ValueError(f'ivector_dir {ivector_dir} has to be either'
                         f' a Path, a string or bolean')
    if not ivector_dir.exists():
        if extractor_dir is None:
            extractor_dir = base_dir / f'exp/nnet3_{train_affix}/extractor'
        else:
            if isinstance(extractor_dir, str):
                extractor_dir = base_dir / f'exp/{extractor_dir}'
        assert extractor_dir.exists()
        print(f'Directory {ivector_dir} not found, estimating ivectors')
        run_process([
            f'steps/online/nnet2/extract_ivectors_online.sh',
            '--cmd', 'run.pl', '--nj', f'{num_jobs}', f'{dataset_dir}',
            f'{extractor_dir}', str(ivector_dir)],
            cwd=str(base_dir),
            stdout=None, stderr=None
        )
    return ivector_dir


def copy_ref_dir(dev_dir, ref_dev_dir, audio_dir, allow_missing_files=True):
    mapping = Chime5KaldiIdMapping()
    required_files = ['utt2spk', 'text']
    with (ref_dev_dir / 'text').open() as file:
        text = file.readlines()
    ref_ids = [line.split(' ', maxsplit=1)[0].strip() for line in text]
    mkdir_p(dev_dir)
    for files in required_files:
        copyfile(str(ref_dev_dir / files), str(dev_dir / files))
    ids = {
    wav_file: mapping.get_array_ids_from_nt_id(wav_file.name.split('.')[0],
                                               channels='ENH')
    for wav_file in audio_dir.glob('*')}
    used_ids = {kaldi_id: wav_file for wav_file, kaldi_ids in ids.items()
                for kaldi_id in kaldi_ids if kaldi_id in ref_ids}
    assert len(used_ids) > 0
    if len(used_ids) < len(ids):
        print(f'Not all files in {audio_dir} were used, '
              f'{len(ids)-len(used_ids)} ids are not used in kaldi')
    elif len(used_ids) < len(ref_ids):
        if not allow_missing_files:
            raise ValueError(
                f'{len(ref_ids)-len(used_ids)} files are missing in {audio_dir}.'
                f' We found only {len(used_ids)} files but expect {len(ref_ids)}'
                f' files')
        print(f'{len(ref_ids)-len(used_ids)} files are missing in {audio_dir}.'
              f' We found only {len(used_ids)} files but expect {len(ref_ids)}'
              f' files. Still continuing to decode the remaining files')
        ref_ids = [_id for _id in used_ids.keys()]
        ref_ids.sort()
        for files in ['utt2spk', 'text']:
            with (dev_dir / files).open() as fd:
                lines = fd.readlines()
                lines = [line for line in lines
                         if line.split(' ')[0] in used_ids]
            (dev_dir / files).unlink()
            with (dev_dir / files).open('w') as fd:
                fd.writelines(lines)

    wavs = [' '.join([kaldi_id, str(used_ids[kaldi_id])]) + '\n'
            for kaldi_id in ref_ids]
    with (dev_dir / 'wav.scp').open('w') as file:
        file.writelines(wavs)


def get_dev_dir(base_dir: Path, org_dir: Path, enh='bss_beam',
                hires=True, ref_dev_dir='dev_beamformit_ref',
                audio_dir=None, num_jobs=8):
    if isinstance(enh, Path):
        dev_dir = enh
    elif 'hires' in enh and hires:
        dev_dir = base_dir / 'data' / f'dev_{enh}'
    elif hires:
        dev_dir = base_dir / 'data' / f'dev_{enh}_hires'
    else:
        dev_dir = base_dir / 'data' / f'dev_{enh}'
    config = 'mfcc_hires.conf' if hires else 'mfcc.conf'
    if not dev_dir.exists():
        print(f'Directory {dev_dir} not found creating data directory')
        if isinstance(ref_dev_dir, str):
            ref_dev_dir = org_dir / 'data' / ref_dev_dir
        assert ref_dev_dir.exists()
        if audio_dir is None:
            copytree(str(ref_dev_dir), str(dev_dir))
        else:
            copy_ref_dir(dev_dir, ref_dev_dir, audio_dir)
        run_process([
            f'{base_dir}/utils/fix_data_dir.sh', str(dev_dir)],
            cwd=str(base_dir), stdout=None, stderr=None
        )
        calculate_mfccs(org_dir, dev_dir, num_jobs=num_jobs,
                        config=config, recalc=True)
    return dev_dir


def create_dest_dir(dest_dir, org_dir=ORG_DIR):
    dest_dir.mkdir(exist_ok=True)
    for file in NEEDED_FILES:
        copyfile(str(org_dir / file), str(dest_dir / file))
    for dirs in NEEDED_DIRS:
        copytree(str(org_dir / dirs), str(dest_dir / dirs), symlinks=True)
    for symlinks in ['steps', 'utils']:
        linkto = os.readlink(str(org_dir / symlinks))
        os.symlink(linkto, str(dest_dir / symlinks))


def decode(model_dir, dest_dir, org_dir, audio_dir: Path,
           ref_dev_dir='dev_beamformit_ref',
           ivector_dir=False, extractor_dir=None,
           hires=True, enh='bss_beam', num_jobs=8):
    '''

    :param model_dir: name of model or Path to model_dir
    :param dest_dir: kaldi egs dir for the decoding
    :param org_dir: kaldi egs dir from which information for decoding are gathered
    :param audio_dir: directory of audio files to decode (may be None)
    :param ref_dev_dir: reference kaldi dataset directory or name for decode dataset
    :param ivector_dir: directory or name for the ivectors (may be None or False)
    :param extractor_dir: directory of the ivector extractor (maybe None)
    :param hires: flag for using high resolution mfcc features (True / False)
    :param enh: name of the enhancement method, used for creating dataset name
    :param num_jobs: number of parallel jobs
    :return:
    '''
    decode_dir = None
    if isinstance(model_dir, str):
        model_dir = org_dir / 'exp' / model_dir
        assert model_dir.exists(), f'{model_dir} does not exist'
    elif isinstance(model_dir, Path):
        if 'tdnn1a' in model_dir.name:
            copytree(str(model_dir), str(
                dest_dir / 'exp' / 'model' / model_dir.parents[0].name))
            model_dir = model_dir.parents[0]
        else:
            if ivector_dir:
                copytree(str(model_dir / 'tdnn1a_sp'),
                         str(dest_dir / 'exp' / 'model' / model_dir.name))
            else:
                copytree(str(model_dir / 'tdnn1a'),
                         str(dest_dir / 'exp' / 'model' / model_dir.name))
        decode_dir = dest_dir / 'exp' / 'model' / model_dir.name / f'decode_{enh}'
    if org_dir and not org_dir == dest_dir:
        create_dest_dir(dest_dir, org_dir)
        os.environ['PATH'] = f'{dest_dir}/utils:{os.environ["PATH"]}'
    train_affix = model_dir.name.split('_', maxsplit=1)[1]
    dev_dir = get_dev_dir(dest_dir, org_dir, enh, hires, ref_dev_dir,
                          audio_dir, num_jobs)
    if ivector_dir:
        ivector_dir = calculate_ivectors(ivector_dir, dest_dir, train_affix,
                                  dev_dir, extractor_dir, num_jobs)
        if decode_dir is None:
            decode_dir = f'{model_dir}/tdnn1a_sp/decode_{enh}'
        os.makedirs(decode_dir)
        run_process([
            f'{org_dir}/steps/nnet3/decode.sh', '--acwt', '1.0',
            '--post-decode-acwt', '10.0',
            '--extra-left-context', '0', '--extra-right-context', '0',
            '--extra-left-context-initial', '0', '--extra-right-context-final',
            '0',
            '--frames-per-chunk', '140', '--nj', '8', '--cmd',
            '"run.pl --mem 4G"',
            '--num-threads', '4', '--online-ivector-dir', str(ivector_dir),
            f'{model_dir}/tree_sp/graph', str(dev_dir), str(decode_dir)],
            cwd=str(dest_dir),
            stdout=None, stderr=None
        )
    else:
        decode_dir = f'{model_dir}/tdnn1a/decode_{enh}'
        os.makedirs(decode_dir)
        run_process([
            f'{org_dir}/steps/nnet3/decode.sh', '--acwt', '1.0',
            '--post-decode-acwt', '10.0',
            '--extra-left-context', '0', '--extra-right-context', '0',
            '--extra-left-context-initial', '0', '--extra-right-context-final',
            '0',
            '--frames-per-chunk', '140', '--nj', '8', '--cmd',
            '"run.pl --mem 4G"', '--num-threads', '4',
            f'{model_dir}/tree_/graph', str(dev_dir),
            str(decode_dir)],
            cwd=str(dest_dir),
            stdout=None, stderr=None
        )


@ex.config
def default():
    train_set = 'train_uall'
    dev_set = 'dev_beamformit_ref'
    org_dir = ORG_DIR
    model_dir = 'chain_train_worn_u100k_cleaned'
    audio_dir = None
    ivector_dir = False
    ref_dev_dir = 'dev_beamformit_ref'
    enh = 'bss_beam'
    extractor_dir = None
    hires = True
    num_jobs = 8


def check_config_element(element):
    if element is not None and not isinstance(element, bool):
        element_path = element
        if Path(element_path).exists():
            element_path = Path(element_path)
    elif isinstance(element, bool):
        element_path = element
    else:
        element_path = None
    return element_path


@ex.automain
def run(_config):
    assert len(ex.current_run.observers) > 0, (
        'FileObserver` missing. Add a `FileObserver` with `-F foo/bar/`.'
    )
    base_dir = ex.current_run.observers[0].basedir
    if isinstance(_config['org_dir'], bool):
        org_dir = base_dir
    else:
        org_dir = _config['org_dir']
    decode(model_dir=check_config_element(_config['model_dir']),
           dest_dir=Path(base_dir),
           org_dir=Path(org_dir),
           audio_dir=check_config_element(_config['audio_dir']),
           ref_dev_dir=check_config_element(_config['ref_dev_dir']),
           ivector_dir=check_config_element(_config['ivector_dir']),
           extractor_dir=check_config_element(_config['extractor_dir']),
           hires=_config['hires'],
           enh=check_config_element(_config['enh']),
           num_jobs=_config['num_jobs']
           )
