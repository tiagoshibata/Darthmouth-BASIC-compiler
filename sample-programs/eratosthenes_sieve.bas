1 LET L = 2000
10 DIM S(L)
20 LET P = 2
30 PRINT P
40 FOR I = P TO L STEP P
50 LET S(I) = 1
60 NEXT I
70 LET P = P + 1
80 IF P = L THEN END
90 IF S(P) = 0 THEN GOTO 30
100 GOTO 70