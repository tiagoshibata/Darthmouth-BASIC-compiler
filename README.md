# Darthmouth BASIC to LLVM IR compiler

BASIC to LLVM IR compiler made from scratch. The generated code can be emulated with LLVM (using `lli`), compiled to Assembly (using `llc`) or compiled to a native binary (using `clang`)

## Language support

The original BASIC grammar is supported, with minor changes. In Wirth notation, the original grammar is given by:

```
1.  Program = BStatement { BStatement } int “END” .
2.  BStatement = int ( Assign | Read | Data | Print | Goto | If | For | Next | Dim | Def | Gosub | Return | Remark ) .
3.  Assign = “LET” Var “=” Exp .
4.  Var = letter digit | letter [ “(” Exp { “,” Exp } “)” ] .
5.  Exp = { “+” | “-” } Eb { ( “+” | “-” | “*” | “/” | “” ) Eb } .
6.  Eb = “(” Exp “)” | Num | Var | ( “FN” letter | Predef ) “(” Exp “)” .
7.  Predef = “SIN” | “COS” | “TAN” | “ATN” | “EXP” | “ABS” | “LOG” | “SQR” | “INT” | “RND” .
8.  Read = “READ” Var { “,” Var } .
9.  Data = “DATA” Snum { “,” Snum } .
10. Print = “PRINT” [ Pitem { “,” Pitem } [ “,” ] ].
11. Pitem = Exp | ““” Character { Character } “”” [ Exp ] .
12. Goto = ( “GOTO” | “GO” “TO” ) int .
13.  If = “IF” Exp ( “>=” | “>” | “<>” | “<” | “<=” | “=” ) Exp “THEN” int .
14.  For = “FOR” letter [ digit ] “=” Exp “TO” Exp [ “STEP” Exp ] .
15. Next = “NEXT” letter [ digit ] .
16. Dim = “DIM” letter “(” int { “,” int } “)” { “,” letter “(” int { “,” int } “)” } .
17. Def = “DEF FN” letter “(” letter [ digit ] “)” “=” Exp .
18. Gosub = “GOSUB” int .
19. Return = “RETURN” .
20. Remark = “REM” { Character } .
21. Int = digit { digit } .
22. Num = ( Int [ “.” { digit } ] | “.” Int ) [ “E” [ “+” | “-” ] Int ] .
23. Snum = [ “+” | “-” ] Num .
24. Character = letter | digit | special .
```

This compiler has the following changes from the original grammar:

* Programs don't have to end with an END statement. Reaching the end of the program automatically ends it. Furthermore, the END statement may appear anywhere in the middle of the program if an early exit is desired.
* According to [BASIC at 50](https://www.dartmouth.edu/basicfifty/commands.html):

> Without a DIM statement, the default dimensions are 0 to 10 for each dimension.

In this compiler, all variables are double precision floating-point scalars, unless explicitly declared as a vector with the DIM statement. Accessing invalid dimensions (e.g. accessing a variable as a vector without an explicit DIM statement) will raise a compilation error. Out-of-bounds accesses give undefined behavior during runtime.
* Variables can have any number of dimensions. In the original BASIC, only vectors and matrices (1 and 2 dimensions) were supported.

## Example BASIC programs

[Examples can be found here.](sample-programs)

## Compilation

After installing this package, run `python -m basic_compiler.main`. The `-h/--help` flag lists supported flags:

```
$ python -m basic_compiler.main -h
usage: main.py [-h] [--opt] [--lli] [--bin BIN] source

BASIC to LLVM IR compiler.

positional arguments:
  source      source file

optional arguments:
  -h, --help  show this help message and exit
  --opt       call optimizer on generated code
  --lli       run generated code with lli
  --bin BIN   call assembler and linker to output a binary
```

## Example

The following program plots a normal distribution:

```basic
10 REM Taken from https://www.dartmouth.edu/basicfifty/commands.html
100 REM PLOT A NORMAL DISTRIBUTION CURVE
120 DEF FNN(X) = EXP(-(X↑2/2))/SQR(2*3.14159265)
140 FOR X = -2 TO 2 STEP .1
150 LET Y = FNN(X)
160 LET Y = INT(100*Y)
170 FOR Z = 1 TO Y
180 PRINT " ",
190 NEXT Z
200 PRINT "*"
210 NEXT X
220 END
```

`python -m basic_compiler.main normal_distribution.bas` outputs to `normal_distribution.ll`:

```llvm
source_filename = "normal_distribution.bas"

@.str1 = private unnamed_addr constant [2 x i8] c" \00", align 1
@.str2 = private unnamed_addr constant [3 x i8] c"%s\00", align 1
@.str3 = private unnamed_addr constant [2 x i8] c"*\00", align 1
@.str4 = private unnamed_addr constant [4 x i8] c"%s\0A\00", align 1
@for_Z_end_12 = internal global double 0., align 8

@X = internal global double 0., align 8
@Y = internal global double 0., align 8
@Z = internal global double 0., align 8

define dso_local void @program(i8* %target_label) local_unnamed_addr #0 {
  indirectbr i8* %target_label, [ label %label_10 ]
label_10:
  ; Taken from https://www.dartmouth.edu/basicfifty/commands.html
  ; PLOT A NORMAL DISTRIBUTION CURVE
  store double -2.0, double* @X, align 8
  br label %label_150
label_150:
  %X_6 = load double, double* @X, align 8
  %FNN_7 = tail call fast double @FNN(double %X_6) #0
  store double %FNN_7, double* @Y, align 8
  %Y_8 = load double, double* @Y, align 8
  %fmul_9 = fmul fast double 100.0, %Y_8
  %INT_10 = tail call fast double @llvm.rint.f64(double %fmul_9) #0
  store double %INT_10, double* @Y, align 8
  store double 1.0, double* @Z, align 8
  %Y_11 = load double, double* @Y, align 8
  store double %Y_11, double* @for_Z_end_12, align 8
  br label %label_180
label_180:
  tail call i32 (i8*, ...) @printf(i8* getelementptr inbounds ([3 x i8], [3 x i8]* @.str2, i32 0, i32 0), i8* getelementptr inbounds ([2 x i8], [2 x i8]* @.str1, i32 0, i32 0)) #0
  %Z_13 = load double, double* @Z, align 8
  %new_Z_14 = fadd fast double %Z_13, 1.0
  store double %new_Z_14, double* @Z, align 8
  %end_Z_15 = load double, double* @for_Z_end_12, align 8
  %will_jump_16 = fcmp ole double %new_Z_14, %end_Z_15
  br i1 %will_jump_16, label %label_180, label %for_exit_17
for_exit_17:
  tail call void @llvm.donothing() readnone #0
  tail call i32 (i8*, ...) @printf(i8* getelementptr inbounds ([4 x i8], [4 x i8]* @.str4, i32 0, i32 0), i8* getelementptr inbounds ([2 x i8], [2 x i8]* @.str3, i32 0, i32 0)) #0
  %X_18 = load double, double* @X, align 8
  %new_X_19 = fadd fast double %X_18, 0.1
  store double %new_X_19, double* @X, align 8
  %will_jump_20 = fcmp ole double %new_X_19, 2.0
  br i1 %will_jump_20, label %label_150, label %for_exit_21
for_exit_21:
  tail call void @llvm.donothing() readnone #0
  tail call void @exit(i32 0) noreturn #0
  unreachable
}

define dso_local i32 @main() local_unnamed_addr #1 {
  tail call void @program(i8* blockaddress(@program, %label_10)) #0
  ret i32 0
}

define dso_local double @FNN(double %arg) local_unnamed_addr #0 {
  %pow_0 = tail call fast double @llvm.pow.f64(double %arg, double 2.0) #0
  %fdiv_1 = fdiv fast double %pow_0, 2.0
  %fdiv_1_neg = fsub fast double 0., %fdiv_1
  %EXP_2 = tail call fast double @llvm.exp.f64(double %fdiv_1_neg) #0
  %fmul_3 = fmul fast double 2.0, 3.14159265
  %SQR_4 = tail call fast double @llvm.sqrt.f64(double %fmul_3) #0
  %fdiv_5 = fdiv fast double %EXP_2, %SQR_4
  ret double %fdiv_5
}

declare void @exit(i32) local_unnamed_addr noreturn #0
declare void @llvm.donothing() local_unnamed_addr readnone #0
declare double @llvm.exp.f64(double) local_unnamed_addr #0
declare double @llvm.pow.f64(double, double) local_unnamed_addr #0
declare double @llvm.rint.f64(double) local_unnamed_addr #0
declare double @llvm.sqrt.f64(double) local_unnamed_addr #0
declare i32 @printf(i8* nocapture readonly, ...) local_unnamed_addr #0

attributes #0 = { nounwind "correctly-rounded-divide-sqrt-fp-math"="false" "disable-tail-calls"="false" "less-precise-fpmad"="false" "no-frame-pointer-elim"="false" "no-infs-fp-math"="true" "no-jump-tables"="false" "no-nans-fp-math"="true" "no-signed-zeros-fp-math"="true" "no-trapping-math"="true" "stack-protector-buffer-size"="8" "target-cpu"="x86-64" "target-features"="+fxsr,+mmx,+sse,+sse2,+x87" "unsafe-fp-math"="true" "use-soft-float"="false" }
attributes #1 = { norecurse nounwind "correctly-rounded-divide-sqrt-fp-math"="false" "disable-tail-calls"="false" "less-precise-fpmad"="false" "no-frame-pointer-elim"="false" "no-infs-fp-math"="true" "no-jump-tables"="false" "no-nans-fp-math"="true" "no-signed-zeros-fp-math"="true" "no-trapping-math"="true" "stack-protector-buffer-size"="8" "target-cpu"="x86-64" "target-features"="+fxsr,+mmx,+sse,+sse2,+x87" "unsafe-fp-math"="true" "use-soft-float"="false" }

!llvm.ident = !{!0}
!0 = !{!"BASIC to LLVM IR compiler (https://github.com/tiagoshibata/pcs3866-compilers)"}
```

This is unoptimized IR generated by the front-end. The `--opt` flag calls `clang` to further optimize the IR. The `FNN` function can be seen with the correct operator priority. Using `--opt`, it is re-written as:

```llvm
define dso_local double @FNN(double %arg) local_unnamed_addr #2 {
  %1 = fmul fast double %arg, %arg
  %fdiv_1_neg = fmul fast double %1, -5.000000e-01
  %EXP_2 = tail call fast double @llvm.exp.f64(double %fdiv_1_neg) #5
  %fdiv_5 = fmul fast double %EXP_2, 0x3FD988453412DD64
  ret double %fdiv_5
}
```

The `pow` call was replaced by a `fmul` instruction, followed by a multiplication by `-0.5`. Then, `exp` is called, and the division by `SQR(2*3.14159265)` is replaced with a multiplication by a constant value.

## More technical info!

https://sites.google.com/view/tiagoshibata-pcs3848/

## Credits

Made for the PCS3848 - Compilers course.

[BASIC at 50 - BASIC Commands](https://www.dartmouth.edu/basicfifty/commands.html) and other online sources were used as references for details of each command.
