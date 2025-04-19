

CREATE TABLE chat_table (
  id bigint NOT NULL PRIMARY KEY,
  name bigint NOT NULL,
  last_message_id bigint NOT NULL,
  creation_date bigint NOT NULL,
  message_status bigint NOT NULL
);


CREATE TABLE user_table (
  id bigint NOT NULL PRIMARY KEY,
  name char NOT NULL,
  surname char NOT NULL,
  patronymic char NOT NULL,
  age bigint NOT NULL,
  description char,
  avatar_path char,
  login char NOT NULL,
  password char NOT NULL,
  type_id bigint NOT NULL
);


CREATE TABLE user_in_chat_table (
  id bigint NOT NULL PRIMARY KEY,
  chat_id bigint NOT NULL,
  user_id bigint NOT NULL
);


CREATE TABLE message_table (
  id bigint NOT NULL PRIMARY KEY,
  from_user_id bigint NOT NULL,
  status boolean NOT NULL,
  date timestamp NOT NULL,
  media char,
  chat_id bigint NOT NULL,
  text char NOT NULL
);


CREATE TABLE user_type (
  id bigint NOT NULL PRIMARY KEY,
  name char NOT NULL
);


CREATE TABLE user_state (
  id bigint NOT NULL PRIMARY KEY,
  user_id bigint NOT NULL,
  emotion_state real NOT NULL,
  physical_state real NOT NULL,
  description char,
  date timestamp NOT NULL,
  reasons char NOT NULL,
  solution char NOT NULL
);

COMMENT ON COLUMN user_state.reasons IS 'Причины плохого самочувствия составляет ии


';
COMMENT ON COLUMN user_state.solution IS 'Предложение по решению проблемы генерит ии, психолог решает, ок или не ок';

CREATE TABLE test_table (
  id bigint NOT NULL PRIMARY KEY,
  name char NOT NULL,
  description char NOT NULL,
  question_amount bigint NOT NULL
);


CREATE TABLE done_test_table (
  id bigint NOT NULL PRIMARY KEY,
  user_id bigint NOT NULL,
  test_id bigint NOT NULL
);


CREATE TABLE patient_table (
  id bigint NOT NULL PRIMARY KEY,
  group_id bigint NOT NULL,
  user_id bigint NOT NULL
);


CREATE TABLE patient_group_table (
  id bigint NOT NULL PRIMARY KEY,
  group_type_id bigint NOT NULL,
  psychologist_id bigint NOT NULL
);


CREATE TABLE group_type_table (
  id bigint NOT NULL PRIMARY KEY,
  name char NOT NULL,
  description char
);


ALTER TABLE user_type ADD CONSTRAINT user_type_id_fk FOREIGN KEY (id) REFERENCES user_table (type_id);
ALTER TABLE user_table ADD CONSTRAINT user_table_id_fk FOREIGN KEY (id) REFERENCES user_state (user_id);
ALTER TABLE user_table ADD CONSTRAINT user_table_id_fk FOREIGN KEY (id) REFERENCES patient_table (user_id);
ALTER TABLE group_type_table ADD CONSTRAINT group_type_table_id_fk FOREIGN KEY (id) REFERENCES patient_group_table (group_type_id);
ALTER TABLE user_table ADD CONSTRAINT user_table_id_fk FOREIGN KEY (id) REFERENCES patient_group_table (psychologist_id);
ALTER TABLE patient_group_table ADD CONSTRAINT patient_group_table_id_fk FOREIGN KEY (id) REFERENCES patient_table (group_id);
ALTER TABLE user_table ADD CONSTRAINT user_table_id_fk FOREIGN KEY (id) REFERENCES user_in_chat_table (user_id);
ALTER TABLE user_in_chat_table ADD CONSTRAINT user_in_chat_table_chat_id_fk FOREIGN KEY (chat_id) REFERENCES chat_table (id);
ALTER TABLE chat_table ADD CONSTRAINT chat_table_id_fk FOREIGN KEY (id) REFERENCES message_table (chat_id);
ALTER TABLE user_table ADD CONSTRAINT user_table_id_fk FOREIGN KEY (id) REFERENCES done_test_table (user_id);
ALTER TABLE test_table ADD CONSTRAINT test_table_id_fk FOREIGN KEY (id) REFERENCES done_test_table (test_id);
