create table users
(
	id varchar(15) not null,
	password varchar(20) not null,
	primary key (id)
);
create table subject
(
	code varchar(2) not null,
	subject_name varchar(20) not null,
	primary key (code)
);
create table lecture
(
	code varchar(2) not null,
	name varchar(20) not null,
	price int not null check (price>=0),
	tutor varchar(15) not null,
	primary key (code, name, price, tutor),
	foreign key (code) references subject (code),
	foreign key (tutor) references users (id)
);
create table enrollment
(
	tutee varchar(15) not null,
	tutor varchar(15) not null,
	code varchar(2) not null,
	lecture_name varchar(20) not null,
	lecture_price int null check (lecture_price>=0),
	foreign key (tutee) references users (id),
	foreign key (tutor) references users (id),
	foreign key (code) references subject (code)
);
create table rating_info
(
	rating varchar(10) not null,
	condition int not null check (condition>=0),
	discount numeric(4,2) not null check (100>discount and discount>=0),
	color_r int not null check (color_r between 0 and 255),
	color_g int not null check (color_g between 0 and 255),
	color_b int not null check (color_b between 0 and 255),
	primary key (rating)
);
create table account
(
	id varchar(15) not null,
	credit int not null check (credit>=0), 
	rating varchar(10) not null,
    role varchar(10) not null check (role in ('tutor', 'tutee')),
	primary key (id),
	foreign key (id) references users (id),
	foreign key (rating) references rating_info (rating)	
);
INSERT INTO users VALUES('admin', '0000');
INSERT INTO users VALUES('postgres', 'dbdb');
INSERT INTO subject VALUES('00', 'history');
INSERT INTO subject VALUES('01', 'mathematics');
INSERT INTO subject VALUES('02', 'language');
INSERT INTO rating_info VALUES('gold', 500000, 2.5, 255, 215, 0);
INSERT INTO rating_info VALUES('silver', 100000, 1, 192, 192, 192);
INSERT INTO rating_info VALUES('bronze', 50000, 0.5, 205, 127, 50);
INSERT INTO rating_info VALUES('welcome', 0, 0, 135, 206, 235);

INSERT INTO account VALUES('admin', 10000000, 'gold', 'tutor');
INSERT INTO account VALUES('postgres', 75000, 'bronze', 'tutee');

INSERT INTO lecture VALUES('00', 'korean history', 1000, 'admin');

INSERT INTO enrollment VALUES('postgres', 'admin', '00', 'korean history',1000);
