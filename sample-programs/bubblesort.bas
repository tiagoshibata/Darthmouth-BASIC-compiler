10 DIM F(20)
12 FOR I = 1 TO 20
14 READ F(I)
20 NEXT I
30 DATA 3, 2, 1, 15, 17, 6, 20, 10, 11, 18, 4, 9, 19, 13, 16, 14, 5, 8, 7, 12
40 LET I = 1
45 LET S = 1
50 IF F(I) <= F(I + 1) THEN GOTO 90
55 LET S = 0
60 LET T = F(I + 1)
70 LET F(I + 1) = F(I)
80 LET F(I) = T
90 LET I = I + 1
100 IF I < 20 THEN GOTO 50
110 IF S = 0 THEN GOTO 40
120 FOR I = 1 TO 20
130 PRINT F(I)
140 NEXT I
