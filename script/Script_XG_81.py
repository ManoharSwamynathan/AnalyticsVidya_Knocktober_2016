# -*- coding: utf-8 -*-
"""
Created on Sat Oct 22 07:20:02 2016

@author: manohar
"""
import xgboost as xgb

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import log_loss, make_scorer
from sklearn.grid_search import GridSearchCV
import gc
import random; random.seed(2016)
from sklearn import metrics
from sklearn.ensemble import RandomForestClassifier

# Load Raw files
print "loading data"
train = pd.read_csv('../input/Train.csv')
test = pd.read_csv('../input/Test.csv')
health_camp_details = pd.read_csv('../input/Health_Camp_Detail.csv')
patient_profile = pd.read_csv('../input/Patient_Profile.csv')
first_health_camp_attended = pd.read_csv('../input/First_Health_Camp_Attended.csv')
second_health_camp_attended = pd.read_csv('../input/Second_Health_Camp_Attended.csv')
third_health_camp_attended = pd.read_csv('../input/Third_Health_Camp_Attended.csv')

print "Data Preparation"
train['Registration_Date'] = pd.to_datetime(train['Registration_Date'])
test['Registration_Date'] = pd.to_datetime(test['Registration_Date'])
health_camp_details['Camp_Start_Date'] = pd.to_datetime(health_camp_details['Camp_Start_Date'])
health_camp_details['Camp_End_Date'] = pd.to_datetime(health_camp_details['Camp_End_Date'])
health_camp_details['camp_lenth'] = (health_camp_details['Camp_End_Date'] - health_camp_details['Camp_Start_Date']).astype('timedelta64[D]').astype(int)

# adding this variable leads to dip on leaderboard
# Calculate number of weekdays between the camp
#num_weekdays=[]
#for index, row in health_camp_details.iterrows():
#        num_weekdays.append(np.busday_count(health_camp_details['Camp_Start_Date'][index], health_camp_details['Camp_End_Date'][index]))
#health_camp_details = pd.concat([health_camp_details, pd.Series(num_weekdays)], axis = 1)
#health_camp_details.columns = ['Health_Camp_ID', 'Camp_Start_Date', 'Camp_End_Date','Category1','Category2','Category3','camp_lenth','num_weekdays']

# This is bring the performance down
# ------------
# Calculate number of weekends between camp start and end date
#health_camp_details['Num_Weekends'] =  health_camp_details['camp_lenth'] - health_camp_details['num_weekdays']
#del health_camp_details['num_weekdays']
#-------------

# import datetime as dt
# health_camp_details['Num_Weekends'] = health_camp_details.apply(np.busday_count(health_camp_details['Camp_Start_Date'], health_camp_details['Camp_End_Date']))

# Camp length distribution
# health_camp_details['camp_lenth'].hist() 
# plt.xlabel('Time between eruptions (min)')
# plt.ylabel('Camp Lenth')

# Checking the data types of the variables
patient_profile.dtypes
patient_profile['First_Interaction'] = pd.to_datetime(patient_profile['First_Interaction'])

first_health_camp_attended.dtypes
# to avoid duplidate columns names during merge
first_health_camp_attended.rename(columns={'Health_Score':'First_Health_Score'}, inplace=True)

second_health_camp_attended.dtypes
# to avoid duplidate columns names during merge
second_health_camp_attended.rename(columns={'Health Score':'Second_Health_Score'}, inplace=True)

third_health_camp_attended.dtypes

# 75278 post drop 74944
train = train[~train.Registration_Date.isnull()]
train.count(axis = 0)
          
# Merge all tables
full_data = pd.concat([train, test])

full_data = pd.merge(full_data, health_camp_details, how='left', on=['Health_Camp_ID'])
full_data = pd.merge(full_data, patient_profile, how='left', on=['Patient_ID'])
full_data = pd.merge(full_data, first_health_camp_attended, how='left', on=['Health_Camp_ID','Patient_ID'])
full_data = pd.merge(full_data, second_health_camp_attended, how='left', on=['Health_Camp_ID','Patient_ID'])
full_data = pd.merge(full_data, third_health_camp_attended, how='left', on=['Health_Camp_ID','Patient_ID'])               

full_data.count(axis = 0)
full_data.dtypes
full_data.describe()

# Fill NA for registration date by adding mean date difference between registration date and camp_Start_date
# full_data[~full_data.Registration_Date.isnull()]
# full_data.Registration_Date.fillna(full_data.Camp_Start_Date + np.timedelta64(2,'D'), inplace=True)
full_data['Register_To_Start'] = (full_data['Registration_Date'] - full_data['Camp_Start_Date']).astype('timedelta64[D]').astype(int)
full_data['Register_To_End'] = (full_data['Registration_Date'] - full_data['Camp_End_Date']).astype('timedelta64[D]').astype(int)
full_data['Register_To_Interaction'] = (full_data['Registration_Date'] - full_data['First_Interaction']).astype('timedelta64[D]').astype(int)

full_data.head()
full_data['Registration_Weekday'] = full_data['Registration_Date'].apply(lambda x: x.weekday())
full_data['Camp_Start_Date_Weekday'] = full_data['Camp_Start_Date'].apply(lambda x: x.weekday())
full_data['Camp_End_Date_Weekday'] = full_data['Camp_End_Date'].apply(lambda x: x.weekday())
full_data['First_Interaction_Weekday'] = full_data['First_Interaction'].apply(lambda x: x.weekday())


full_data['Registration_month'] = full_data['Registration_Date'].apply(lambda x: x.month)
full_data['Camp_Start_Date_month'] = full_data['Camp_Start_Date'].apply(lambda x: x.month)
full_data['Camp_End_Date_month'] = full_data['Camp_End_Date'].apply(lambda x: x.month)
full_data['First_Interaction_month'] = full_data['First_Interaction'].apply(lambda x: x.month)

full_data['Registration_day'] = full_data['Registration_Date'].apply(lambda x: x.day)
full_data['Camp_Start_Date_day'] = full_data['Camp_Start_Date'].apply(lambda x: x.day)
full_data['Camp_End_Date_day'] = full_data['Camp_End_Date'].apply(lambda x: x.day)
full_data['First_Interaction_day'] = full_data['First_Interaction'].apply(lambda x: x.day)

# Populate the target variable
full_data['target'] = np.where(((full_data['First_Health_Score'] >0 ) | (full_data['Second_Health_Score'] > 0) | (full_data['Number_of_stall_visited'] > 0)) , 0, 1)
full_data['target'].value_counts()

full_data.count()
full_data.head(n=10)

cat_cols = ['Category1','Category2','City_Type','Employer_Category', 'Income','Education_Score','Age']

full_data['Income'] = np.where(full_data['Income'] == 'None', 7, full_data['Income']) 
full_data['Education_Score'] = np.where(full_data['Education_Score'] == 'Education_None', 0, full_data['Education_Score'])
full_data['Age'] = np.where(full_data['Age'] == 'Age_None', 0, full_data['Age'])
full_data = full_data.fillna('None')
full_data['City_Type'] = np.where(full_data['City_Type'] == 'City_Type_None', 0, full_data['City_Type'])
full_data['Employer_Category'] = np.where(full_data['Employer_Category'] == 'Employer_Category_None', 0, full_data['Employer_Category'])

le = LabelEncoder()
for feature in cat_cols:
    full_data [feature] = le.fit_transform(full_data[feature])

full_data = full_data.drop(['Health_Camp_ID', 'Registration_Date', 'Camp_Start_Date', 'Camp_End_Date', 'First_Interaction','Number_of_stall_visited','Last_Stall_Visited_Number','First_Health_Score','Second_Health_Score','Donation'], axis=1)

# full_data.to_csv('full_data.csv', index=False)

full_data['target'].value_counts()

full_data.head()

# Normalize variables.... this did not help much to improve the accuracy
#from sklearn.preprocessing import MinMaxScaler
#min_max=MinMaxScaler()
#
#full_data['camp_length'] = min_max.fit_transform(full_data['camp_lenth'])
#full_data['Register_To_Start'] = min_max.fit_transform(full_data['Register_To_Start'])
#full_data['Register_To_End'] = min_max.fit_transform(full_data['Register_To_End'])
#full_data['Register_To_Interaction'] = min_max.fit_transform(full_data['Register_To_Interaction'])


train_full = full_data.ix[:74943, :]
test = full_data.ix[74944:, :]

y_train_full = train_full['target']
# Train full
train_full_X = train_full

msk = np.random.rand(len(train_full)) < 0.8
train = train_full[msk]
validate = train_full[~msk]

y_train = train['target']
train_X = train
train_X.drop(['Patient_ID','target'], axis=1, inplace=True)

y_validate = validate['target']
validate_X = validate
validate_X.drop(['Patient_ID','target'], axis=1, inplace=True)

test_X = test
test_X.drop(['Patient_ID','target'], axis=1, inplace=True)

train_full_X.drop(['Patient_ID','target'], axis=1, inplace=True)

target = 'target'
IDcol = 'Patient_ID'
predictors = [x for x in train.columns if x not in [target, IDcol]]

# You can experiment with many other options here, using the same .fit() and .predict()
# methods; see http://scikit-learn.org
# This example uses the current build of XGBoost, from https://github.com/dmlc/xgboost
print "Building the model"
gbm = xgb.XGBClassifier(max_depth=4, 
                        n_estimators=5000, 
                        learning_rate=0.01,
                        min_child_weight=6,
                        subsample=0.8,
                        colsample_bytree=0.8,
                        reg_alpha=0.005,
                        gamma=0,
                        objective= 'binary:logistic',
                        nthread=4,
                        scale_pos_weight=1,
                        seed=2016).fit(train_full_X[predictors], y_train_full)

print "Predicting on train"
predictions = gbm.predict(train_X[predictors])
predictions_prob = gbm.predict_proba(train_X[predictors])[:,1]

# Print model report:
print "Accuracy : %.4g" % metrics.accuracy_score(y_train, predictions)
print "AUC Score (Train): %f" % metrics.roc_auc_score(y_train, predictions_prob)

print "Predicting on validate"
predictions = gbm.predict(validate_X[predictors])
predictions_prob = gbm.predict_proba(validate_X[predictors])[:,1]

# Print model report:
print "Accuracy : %.4g" % metrics.accuracy_score(y_validate, predictions)
print "AUC Score (Validate): %f" % metrics.roc_auc_score(y_validate, predictions_prob)

print "Predicting on train full"
predictions = gbm.predict(train_full_X[predictors])
predictions_prob = gbm.predict_proba(train_full_X[predictors])[:,1]

# Print model report:
print "Accuracy : %.4g" % metrics.accuracy_score(y_train_full, predictions)
print "AUC Score (Train Full): %f" % metrics.roc_auc_score(y_train_full, predictions_prob)

# Predict for test data
print "Predicting on test"
outcome = gbm.predict_proba(test)[:,1]

# Create File for final submission
print "Writing results"
test_raw = pd.read_csv('../input/Test.csv')
submission = pd.concat([test_raw.ix[:,0:2], pd.Series(outcome)], axis = 1)
submission.columns = ['Patient_ID','Health_Camp_ID','Outcome']

submission.to_csv('Submission_xgboost_81.csv',index=False)
