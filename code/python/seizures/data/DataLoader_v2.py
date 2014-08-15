import glob
from os.path import join
import os;
from seizures.data.EEGData import EEGData
import numpy as np
from seizures.features.FFTFeatures import FFTFeatures
from seizures.features.FeatureExtractBase import FeatureExtractBase

# Wittawat: Many load_* methods do not actually use the patient_name argument

class DataLoader(object):
    """
    Class to load data (all segments) for a patient
    Loading from individual files (not the stitched data)
    @author Vincent (from Shaun original loader)
    """

    def __init__(self, base_dir, feature_extractor):
        """
        base_dir: path to the directory containing patient folders i.e., directory 
        containing Dog_1/, Dog_2, ..., Patient_1, Patient_2, ....
        """
        if not os.path.isdir(base_dir):
            raise ValueError('%s is not a directory.' % base_dir)
        if not isinstance(feature_extractor, FeatureExtractBase):
            raise ValueError('feature_extractor must be an instance of FeatureExtractBase')

        self.base_dir = base_dir
        self.feature_extractor = feature_extractor
        # patient_name = e.g., Dog_1
        self.patient_name = None
        # type_labels = a list of {0, 1}. Indicators of a seizure (1 for seizure).
        self.type_labels = None
        # early_labels = a list of {0, 1}. Indicators of an early seizure 
        # (1 for an early seizure).
        self.early_labels = None
        # a list of numpy arrays. Each element is from feature_extractor.extract()
        # The length of the list is the number of time steps in the data segment 
        # specified by patient_name. For example, len=400 in Dog_1 
        self.features_train = None
        # a list of numpy arrays. Each element is from feature_extractor.extract()
        self.features_test = None
        # list of file names in base_dir directory
        self.files = None
        self.files_nopath = None

    def load_data(self, patient_name, type='training'):
        """
        Loads data for a patient and a type of data into class variables
        No output
        :param name: str
        """
        self.patient_name = patient_name
        self._reset_lists()
        # For type='training', this will get all interictal and ictal file names
        files = self._get_files_for_patient(type)
        
        # reorder files so as to mix a bit interictal and ictal (to fasten debug I crop the files to its early entries)
        if type == 'training':
            files_interictal = [f for f in files if f.find("_interictal_") >= 0 ]
            print '%d interictal segments for %s'%(len(files_interictal), patient_name)
            files_ictal = [f for f in files if f.find("_ictal_") >= 0]
            print '%d ictal segments for %s'%(len(files_ictal), patient_name)
            files = []
            # The following loop just interleaves ictal and interictal segments
            # so that we have 
            #[ictal_segment1, interictal_segment1, ictal_segment2, ...]
            for i in range(max(len(files_ictal), len(files_interictal))):
                if i < len(files_ictal):
                    files.append(files_ictal[i])
                if i < len(files_interictal):
                    files.append(files_interictal[i])

        np.random.seed(0)
        I = np.random.permutation(len(files))
        #I = range(len(files))
        ## Wittawat: why 0:400 ? So Vincent just wants things to be faster ?
        total_segments = len(files_interictal) + len(files_ictal)
        subsegments = min(400, total_segments)
        print 'subsampling from %d segments to %d'% (total_segments, subsegments)
        self.files = [files[i] for i in I[0:subsegments]]

        #self.files = [files[i] for i in I[0:200]]
        #self.files = files

        i = 0.
        for filename in self.files:
            print i/len(self.files)*100.," percent complete         \r",
            # Each call of _load_data_from_file appends data to features_train 
            # features_test lists depending on the (type) variable. 
            # It also appends data to type_labels and early_labels.
            self._load_data_from_file(patient_name, filename)
            i+=1
        print "\ndone"

    def training_data(self, patient_name):
        """
        returns features as a matrix of 1D np.ndarray
        returns classification vectors as 1D np.ndarrays
        :param patient_name:
        :return: feature matrix and labels
        """
        print "\nLoading train data for " + patient_name
        self.load_data(patient_name, type='training')
        X = self._merge_vectors_into_matrix(self.features_train)
        return X, np.array(self.type_labels), np.array(self.early_labels)

    def blocks_for_Xvalidation(self, patient_name,n_fold =3):
        """
        Stratified partitions (partition such that class proportion remains same 
        in each data fold) of data for cross validation. The sum of instances 
        in all partitions may be less than the original total.
        returns
        - a list of 2D ndarrays of features
        - a list of 1D ndarrays of type_labels
        - a list of 1D ndarrays of early_labels
        All the lists have length = n_fold. 
        These outputs can be used with XValidation.

        :param patient_name:
        :return: feature matrix and labels
        """
        # y1 = type_labels,  y2 = early_labels
        X,y1,y2 = self.training_data(patient_name)
        n = len(y1)

        assert(np.sum(y2)>n_fold)
        # do blocks for labels=1 and labels=0 separetaly and merge at the end
        # the aim is to always have both labels in each train/test sets
        Iy2_1 = np.where(y2==1)[0].tolist()
        Iy2_0 = np.where(y2==0)[0].tolist()
        assert(np.sum(Iy2_1)>n_fold)

        def chunks(l, n_block):
            """ Yield n_block blocks.
            """
            m = len(l)/n_block
            r = len(l)%n_block
            for i in xrange(0, n_block):
                if i == n_block-1:
                    yield l[i*m:-1]
                else:
                    yield l[i*m:(i+1)*m]

        Iy2_1_list = list(chunks(Iy2_1, n_fold))
        Iy2_0_list = list(chunks(Iy2_0, n_fold))
        #print len(Iy2_1_list)
        assert(len(Iy2_0_list)==n_fold)
        assert(len(Iy2_1_list)==n_fold)
        Iy2 = [Iy2_1_list[i]+Iy2_0_list[i] for i in range(n_fold)]


        y1p = [ y1[Iy2[i]] for i in range(n_fold)]
        y2p = [ y2[Iy2[i]] for i in range(n_fold)]
        Xp = [ X[Iy2[i],:] for i in range(n_fold)]

        return Xp,y1p,y2p

    def test_data(self, patient_name):
        """
        returns features as a matrix of 1D np.ndarray
        :rtype : numpy 2D ndarray
        :param name: str
        """
        print "\nLoading test data for " + patient_name
        self.load_data(patient_name, type='test')
        return self._merge_vectors_into_matrix(self.features_test)


    def _reset_lists(self):
        self.episode_matrices = []
        self.type_labels = []
        self.early_labels = []

    def _get_files_for_patient(self, type="training"):
        assert (type in ["test", "training"])
        if type == "training":
            self.features_train = []
            files = glob.glob(join(self.base_dir, self.patient_name + '/*ictal*'))

        elif type == "test":
            self.features_test = []
            self.early_labels = []
            self.type_labels = []
            files = glob.glob(join(self.base_dir, self.patient_name + '/*test*'))
        # files_nopath = [os.path.basename(x) for x in files]
        #self.files_nopath = files_nopath
        return files


    def _load_data_from_file(self, patient, filename):
        if filename.find('test') != -1:
            # if filename is a test segment
            self._load_test_data_from_file(patient, filename)
        else:
            self._load_training_data_from_file(patient, filename)


    def _load_training_data_from_file(self, patient, filename):
        """
        Loading single file training data
        :param patient:
        :param filename:
        :return:
        """
        #print "\nLoading train data for " + patient + filename
        eeg_data_tmp = EEGData(filename)
        # a list of Instance's
        eeg_data = eeg_data_tmp.get_instances()
        assert len(eeg_data) == 1
        # eeg_data is now an Instance
        eeg_data = eeg_data[0]
        if filename.find('interictal') > -1:
            y_seizure=0
            y_early=0
        elif eeg_data.latency < 15:
            y_seizure=1
            y_early=1
        else:
            y_seizure=1
            y_early=0
        x = self.feature_extractor.extract(eeg_data)
        self.features_train.append(np.hstack(x))
        self.type_labels.append(y_seizure)
        self.early_labels.append(y_early)

    def _load_test_data_from_file(self, patient, filename):
        """
        Loading single file test data
        :param patient:
        :param filename:
        :return:
        """
        assert ( filename.find('test'))
        print "\nLoading test data for " + patient + filename
        eeg_data_tmp = EEGData(filename)
        eeg_data = eeg_data_tmp.get_instances()
        assert len(eeg_data) == 1
        eeg_data = eeg_data[0]
        x = self.feature_extractor.extract(eeg_data)
        self.features_test.append(np.hstack(x))


    def _get_feature_vector_from_instance(self, instance):
        return self.feature_extractor.extract(instance)

    def _merge_vectors_into_matrix(self, feature_vectors):
        n = len(feature_vectors)
        d = len(feature_vectors[0])
        matrix = np.zeros((n, d))
        for i, _ in enumerate(feature_vectors):
            matrix[i, :] = feature_vectors[i].T
        return matrix

    def labels(self, patient):
        # Wittawat: Why do we need patient argument ? 
        assert (self.patient_name == patient)
        return self.type_labels, self.early_labels

