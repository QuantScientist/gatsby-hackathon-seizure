import os
from pandas import DataFrame, read_csv
from seizures.data.DataLoader import DataLoader

from seizures.data.EEGData import EEGData
from seizures.features.FeatureExtractBase import FeatureExtractBase
from seizures.prediction.PredictorBase import PredictorBase


class SubmissionFile():
    """
    Class to generate submission files
    
    @author Heiko
    """
    
    def __init__(self, data_path):
        """
        Constructor
        
        Parameters:
        data_path   - / terminated path of test data
        """
        self.data_path = data_path
        
        # generate dog and patient record names
        self.patients = ["Dog_%d" % i for i in range(1, 5)] + ["Patient_%d" % i for i in range(1, 9)]
    
    @staticmethod
    def get_submission_filenames():
        """
        Returns a data-frame with all filenames of the sample submission file
        """
        me = os.path.dirname(os.path.realpath(__file__))
        data_dir = os.sep.join(me.split(os.sep)[:-4]) + os.sep + "data"
        fname = data_dir + os.sep + "sampleSubmission.csv"
        return [row[1] for row in read_csv(fname)["clip"]]
        
    def generate_submission(self, predictor_seizure, predictor_early,
                            feature_extractor, output_fname="output.csv"):
        """
        Generates a submission file for a given pair of predictors, which will
        be trained on all training data per patient/dog instance.
        
        Parameters:
        predictor_seizure - Instance of PredictorBase, fixed parameters
        predictor_early   - Instance of PredictorBase, fixed parameters
        feature_extractor - Instance of FeatureExtractBase, to extract test features
        output_fname      - Optional filename for result submission file
        """
        # make sure given objects are valid
        assert(isinstance(predictor_seizure, PredictorBase))
        assert(isinstance(predictor_early, PredictorBase))
        assert(isinstance(feature_extractor, FeatureExtractBase))
        
        # load filenames
        fnames = SubmissionFile.get_submission_filenames()
        
        # predict on test data, iterate over patients and dogs
        # and the in that over all test files
        result = DataFrame(columns=('clip', 'seizure', 'early'))

        data_loader = DataLoader(self.data_path, feature_extractor)

        for patient in self.patients:
            # load training data
            print "Loading data for " + patient
            X = data_loader.training_data(patient)
            y_seizure, y_early = data_loader.labels(patient)
        
            # train both models
            print "Training seizure for " + patient
            predictor_seizure.fit(X, y_seizure)
            print "Training early for " + patient
            predictor_early.fit(X, y_early)
            
            # find out filenames that correspond to patient/dog
            fnames_patient = []
            for fname in fnames:
                if patient in fname:
                    fnames_patient + [fname]
            
            # now predict on all test points
            for fname in fnames_patient:
                print "Loading test data for " + fname
                eeg_data = None  # EEGData(fname)
                X = feature_extractor.extract(eeg_data)
                
                # predict
                print "Predicting seizure for " + fname
                pred_seizure = predictor_seizure.predict(X)
                
                print "Predicting seizure for " + fname
                pred_early = predictor_seizure.predictor_early(X)
                
                # store
                result.append({'clip':fname, 'seizure':pred_seizure, 'early':pred_early})
        
        result.to_csv(self.data_path + output_fname, result)
