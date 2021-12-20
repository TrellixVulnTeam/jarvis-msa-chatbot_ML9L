from gensim.models import Word2Vec
from konlpy.tag import Komoran
import time
import pandas as pd
import tensorflow as tf
from tensorflow.keras import preprocessing
from tensorflow.keras.models import Model, load_model
from tensorflow.keras.layers import Input, Embedding, Dense, Dropout, Conv1D, GlobalMaxPool1D, concatenate

class Classificationmodel:
    def __init__(self):
        pass

    def execute(self):

        start = time.time()

        print('말뭉치 데이터 읽기')
        question_data = pd.read_csv('../data/intent_data.csv')
        question_data = question_data['Q']
        print(question_data)
        print('데이터 읽기 완료: ', time.time() - start)

        komoran = Komoran(userdic='./data/user_nng.tsv')

        docs = [komoran.nouns(sentence) for sentence in question_data]
        print(docs)
        print(komoran.pos(question_data[0]))
        print(docs[0])

        # word2Vec 모델 학습
        model = Word2Vec(sentences=docs, vector_size=200, window=4, min_count=2, sg=1)

        # 코퍼스 모델 저장
        model.save('./data/cupus.model')

        print("copus_count : ", model.corpus_count)
        print("copus_total_words : ", model.corpus_total_words)

    def model_load(self):
        model = Word2Vec.load('./data/copus.model')

    def train(self):
        train_flie = './data/Q&A.csv'
        data = pd.read_csv(train_flie)
        fetures = data['question'].tolist()
        label = data['intentNumber'].tolist()
        # fetures = data['Q'].tolist()
        # label = data['label'].tolist()

        corpus = [preprocessing.text.text_to_word_sequence(text) for text in fetures]

        tokenizer = preprocessing.text.Tokenizer()
        tokenizer.fit_on_texts(corpus)
        sequences = tokenizer.texts_to_sequences(corpus)
        word_index = tokenizer.word_index
        MAX_SEQ_LEN = 50 #단어 시퀸스 백터 크기
        padded_seqs = preprocessing.sequence.pad_sequences(sequences, maxlen=MAX_SEQ_LEN, padding='post')

        # 학습용, 검증용, 테스트용  데이터셋 생성
        # 데이터 셋 비율 = 7:2:1

        ds = tf.data.Dataset.from_tensor_slices((padded_seqs, label))
        ds = ds.shuffle(len(sequences))
        train_size = int(len(padded_seqs) * 0.7)
        val_size = int(len(padded_seqs) * 0.2)
        test_size = int(len(padded_seqs) * 0.1)
        train_ds = ds.take(train_size).batch(20)
        val_ds = ds.skip(train_size).take(val_size).batch(20)
        test_ds = ds.skip(train_size + val_size).take(test_size).batch(20)

        # 하이퍼 파라미터 설정
        dropout_prob = 0.5
        EMB_SIZE = 128
        EPOCH = 10
        VOCAB_SIZE = len(word_index) + 1 # 전체 단어의 수

        # CNN 모델 정의
        input_layer = Input(shape=(MAX_SEQ_LEN,))
        embedding_layer = Embedding(VOCAB_SIZE, EMB_SIZE, input_length=MAX_SEQ_LEN)(input_layer)
        dropout_emb = Dropout(rate=dropout_prob)(embedding_layer)

        conv1 = Conv1D(filters=128, kernel_size=3, padding='valid', activation=tf.nn.relu)(dropout_emb)
        pool1 = GlobalMaxPool1D()(conv1)
        conv2 = Conv1D(filters=128, kernel_size=4, padding='valid', activation=tf.nn.relu)(dropout_emb)
        pool2 = GlobalMaxPool1D()(conv2)
        conv3 = Conv1D(filters=128, kernel_size=5, padding='valid', activation=tf.nn.relu)(dropout_emb)
        pool3 = GlobalMaxPool1D()(conv3)

        # 3, 4, 5 -gram 이후 합치기
        concat = concatenate([pool1, pool2, pool3])
        hidden = Dense(128, activation=tf.nn.relu)(concat)
        dropout_hidden = Dropout(rate=dropout_prob)(hidden)
        logits = Dense(3, name='logits')(dropout_hidden)
        predictions = Dense(3, activation=tf.nn.softmax)(logits)

        #  모델 생성
        model = Model(inputs=input_layer, outputs=predictions)
        model.compile(optimizer='adam', loss='sparse_categorical_crossentropy',metrics=['accuracy'])

        # 모델 학습
        model.fit(train_ds, validation_data=val_ds, epochs=EPOCH, verbose=1)

        # 모델 평가(테스트 데이터셋 이용)
        loss, accuracy = model.evaluate(test_ds, verbose=1)
        # print('Accuracy :  $f' % (accuracy * 100))
        # print('loss : %f' % (loss))

        # 모델 저장
        model.save('class_model3.h5')

    def execute_predict(self):
        # 데이터 읽어오기
        train_file = "../data/intent_data.csv"
        data = pd.read_csv(train_file, delimiter=',')
        features = data['Q'].tolist()
        labels = data['label'].tolist()

        # 단어 인덱스 시퀀스 벡터
        corpus = [preprocessing.text.text_to_word_sequence(text) for text in features]
        tokenizer = preprocessing.text.Tokenizer()
        tokenizer.fit_on_texts(corpus)
        sequences = tokenizer.texts_to_sequences(corpus)
        MAX_SEQ_LEN = 50  # 단어 시퀀스 벡터 크기
        padded_seqs = preprocessing.sequence.pad_sequences(sequences, maxlen=MAX_SEQ_LEN, padding='post')

        # 테스트용 데이터셋 생성
        ds = tf.data.Dataset.from_tensor_slices((padded_seqs, labels))
        ds = ds.shuffle(len(features))
        test_ds = ds.take(2000).batch(20)  # 테스트 데이터셋

        # 감정 분류 CNN 모델 불러오기
        model = load_model('../model/cl_model.h5')
        model.summary()
        model.evaluate(test_ds, verbose=2)

        # # TEST 12.17
        # sample_txt = '미열과 잦은 기침이 있어요 코로나일까요?'

        # 테스트용 데이터셋의 10212번째 데이터 출력
        print("단어 시퀀스 : ", corpus[312])
        print("단어 인덱스 시퀀스 : ", padded_seqs[312])
        print("문장 분류(정답) : ", labels[312])

        # 테스트용 데이터셋의 10212번째 데이터 감정 예측
        picks = [312]
        predict = model.predict(padded_seqs[picks])
        predict_class = tf.math.argmax(predict, axis=1)
        print("의도 예측 점수 : ", predict)
        print("의도 예측 클래스 : ", predict_class.numpy())


if __name__ == '__main__':
    chat = Classificationmodel()
    # chat.execute()
    chat.train()
    # chat.execute_predict()