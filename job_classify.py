
"""Classifying Job Posts

#Classifying Job Posts Tutorial
## Using Google Universal Sentence Encoder

The Universal Sentence Encoder makes getting sentence level embeddings as easy as it has historically been to lookup the embeddings for individual words. The sentence embeddings can then be trivially used to compute sentence level meaning similarity as well as to enable better performance on downstream classification tasks using less supervised training data.

# Getting Started

This section sets up the environment for access to the Universal Sentence Encoder on TF Hub and provides examples of applying the encoder to words, sentences, and paragraphs.
"""

# Install the latest Tensorflow version.
!pip3 install --quiet "tensorflow>=1.7"
# Install TF-Hub.
!pip3 install --quiet tensorflow-hub
!pip3 install seaborn
!pip3 install bs4
!pip3 install keras

"""More detailed information about installing Tensorflow can be found at [https://www.tensorflow.org/install/](https://www.tensorflow.org/install/)."""

import tensorflow as tf
import tensorflow_hub as hub
import matplotlib.pyplot as plt
import numpy as np
import os
import pandas as pd
import re
import seaborn as sns
import json
from bs4 import BeautifulSoup
import unicodedata
import re
import keras.layers as layers
from keras.models import Model
from keras import backend as K
np.random.seed(10)

from google.colab import drive
drive.mount('/content/drive')

"""Data Pre Processing"""

def remove_special_characters(text, remove_digits=False):
	pattern = r'[^a-zA-z0-9\s]' if not remove_digits else r'[^a-zA-z\s]'
	text = re.sub(pattern, '', text)
	return text

with open('drive/My Drive/sampleJobDataWithTags.json') as json_data:
	training_data = json.load(json_data)
	print("Total Training samples",len(training_data))


	#getting unique tags
	unique_tags = []
	for d in training_data:
		for tag in d["tags"]:
			if tag not in unique_tags:
				unique_tags.append(tag)

	print("Total Unique Tags",len(unique_tags))
	
	#finding tags distributions(finding unique tags)
	distribution = {}
	for tag in unique_tags:
		for data in training_data:
			if tag in data["tags"]:
				if tag in distribution.keys():
					distribution[tag] += 1
				else:
					distribution[tag] = 1


	#data cleansing
	for data in training_data:
		#remove html tags
		data["title"] = BeautifulSoup(data["title"], "html.parser").get_text()
		data["description"] = BeautifulSoup(data["description"], "html.parser").get_text()
		#remove accented data
		data["title"] = unicodedata.normalize('NFKD', data["title"]).encode('ascii', 'ignore').decode('utf-8', 'ignore')
		data["description"] = unicodedata.normalize('NFKD', data["description"]).encode('ascii', 'ignore').decode('utf-8', 'ignore')
		#remove special characters
		data["title"]  = remove_special_characters(data["title"])
		data["description"]  = remove_special_characters(data["description"])
		#converting to lowercase
		data["title"] = data["title"].lower()
		data["description"] = data["description"].lower()

	
	splitted_training_data = []
	for data in training_data:
		for tag in data["tags"]:
			splitted_training_data.append({"title": data["title"], "description": data["description"], "tag": tag})

	training_data= splitted_training_data
	print(training_data[0])

# converting json array to dataframe
train = pd.read_json(json.dumps(training_data))
train.head()
list1 = ((train["description"]).values.tolist())
list2 = (train["title"].values.tolist())
train_list = list1 + list2

module_url = "https://tfhub.dev/google/universal-sentence-encoder-large/3" #@param ["https://tfhub.dev/google/universal-sentence-encoder/2", "https://tfhub.dev/google/universal-sentence-encoder-large/3"]

# Import the Universal Sentence Encoder's TF Hub module
embed = hub.Module(module_url)

# For test purpose.
#word = "Elephant"
#sentence = "I am a sentence for which I would like to get its embedding."
#paragraph = (
#    "Universal Sentence Encoder embeddings also support short paragraphs. "
#    "There is no hard limit on how long the paragraph is. Roughly, the longer "
#    "the more 'diluted' the embedding will be.")
#messages = [word, sentence, paragraph]
#print("Type of messages",type(messages))

# Reduce logging output.
tf.logging.set_verbosity(tf.logging.ERROR)

with tf.Session() as session:
  session.run([tf.global_variables_initializer(), tf.tables_initializer()])
  message_embeddings = session.run(embed(train_list))

  for i, message_embedding in enumerate(np.array(message_embeddings).tolist()):
    print("Message: {}".format(train_list[i]))
    print("Embedding size: {}".format(len(message_embedding)))
    message_embedding_snippet = ", ".join(
        (str(x) for x in message_embedding[:3]))
    print("Embedding: [{}, ...]\n".format(message_embedding_snippet))

# Compute a representation for each message, showing various lengths supported.
messages = ["That band rocks!", "That song is really cool."]

with tf.Session() as session:
  session.run([tf.global_variables_initializer(), tf.tables_initializer()])
  message_embeddings = session.run(embed(messages))
message_embeddings

embed_size = embed.get_output_info_dict()['default'].get_shape()[1].value
embed_size

unique_tags = train.tag.unique()
unique_tags

tags_distribution = train.groupby('tag').nunique()
tags_distribution

train.tag.hist()

category_counts = len(train.tag.unique())
category_counts

"""## Wrap embed module in a Lambda layer
Explicitly cast the input as a string
"""

def UniversalEmbedding(x):
    return embed(tf.squeeze(tf.cast(x, tf.string)), signature="default", as_dict=True)["default"]

input_text = layers.Input(shape=(1,), dtype=tf.string)
embedding = layers.Lambda(UniversalEmbedding, output_shape=(embed_size,))(input_text)
dense = layers.Dense(256, activation='relu')(embedding)
pred = layers.Dense(category_counts, activation='softmax')(dense)
model = Model(inputs=[input_text], outputs=pred)
model.compile(loss='categorical_crossentropy', optimizer='adam', metrics=['accuracy'])
model.summary()

train_text = train['title'].tolist()
train_text = np.array(train_text, dtype=object)[:, np.newaxis]

#One hot encoding of labels
train_label = np.asarray(pd.get_dummies(train.tag), dtype = np.int8)

train_text.shape

train_label.shape

train_label[:3]

#splitting into train and test
import math

splitted = np.split(train_text,[math.ceil(len(train_text)*0.8)])
train_text= splitted[0]
test_text= splitted[1]
print("Training examples: ", len(train_text))
print("Test examples: ",len(test_text))

splitted = np.split(train_label,[math.ceil(len(train_label)*0.8)])
train_label= splitted[0]
test_label= splitted[1]

print("Training labels: ", len(train_label))
print("Test labes: ",len(test_label))

"""## Train Keras model and save weights
This only train and save our Keras layers not the embed module' weights.
"""

with tf.Session() as session:
  K.set_session(session)
  session.run(tf.global_variables_initializer())
  session.run(tf.tables_initializer())
  history = model.fit(train_text, 
            train_label,
            validation_data=(test_text, test_label),
            epochs=50,
            batch_size=32)
  model.save_weights('./model.h5')

!ls -alh | grep model.h5

"""## Make predictions"""

new_text = ["We are looking for Social media professional"]
new_text = np.array(new_text, dtype=object)[:, np.newaxis]
with tf.Session() as session:
  K.set_session(session)
  session.run(tf.global_variables_initializer())
  session.run(tf.tables_initializer())
  model.load_weights('./model.h5')  
  predicts = model.predict(new_text, batch_size=32)

predicts

categories = train.tag.cat.categories.tolist()
predict_logits = predicts.argmax(axis=1)
predict_labels = [categories[logit] for logit in predict_logits]
predict_labels
