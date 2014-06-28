'''
Created on 28 Jun 2014

@author: heiko
'''
from seizures.features.RandomFeatures import RandomFeatures
from seizures.prediction.RandomPredictor import RandomPredictor
from seizures.submission.SubmissionFile import SubmissionFile


if __name__ == '__main__':
    predictor = RandomPredictor()
    extractor = RandomFeatures()
    
    test_files = SubmissionFile.get_submission_filenames()[:10]
    data_path = "/home/heiko/data/seizure/"
    
    submission = SubmissionFile(data_path)
    submission.generate_submission(predictor, predictor,
                            extractor, test_filenames=test_files)