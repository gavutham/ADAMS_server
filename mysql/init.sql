use attendance_management;

drop table if exists student;
drop table if exists subject;
drop table if exists teacher;
drop table if exists teacher_sub;
drop table if exists attendance;
drop table if exists period;


create table student(
email varchar(100) primary key,
st_name varchar(20),
class varchar(10)
);

create table subject(
sub_code varchar(10) primary key,
sub_name varchar(40)
);

create table teacher(
teach_id varchar(10) primary key,
teacher_name varchar(20)
);

create table teacher_sub(
Teach_id varchar(10),
sub_code varchar(10),
class varchar(10)
);

create table attendance(
s_no integer primary key auto_increment,
email varchar(100),
sub_code varchar(10),
prd integer,
attd_date date
);

create table period(
prd integer primary key,
st_time time,
end_time time
);