class Print:
    def __init__(self, state):
        self.state = state

    def newline(self):
        self.state.external_symbols.add('putchar')
        self.state.append_instruction('tail call i32 @putchar(i32 10) #0')

    def const_string(self, literal, newline=False):
        # Create a constant null-terminated string, global to this module
        string_constant_identifier = '@.str{}'.format(len(self.state.private_globals))
        # Add one byte for the null-terminator and don't count escape sequences
        string_length = len(literal) + 1 - 2 * literal.count('\\')
        self.state.private_globals.append(
            '{} = private unnamed_addr constant [{} x i8] c"{}\\00", align 1'
            .format(string_constant_identifier, string_length, literal))
        return string_constant_identifier, string_length

    def string(self, element):
        self.state.print_parameters.append(element)

    def expression_result(self):
        self.state.print_parameters.append(self.state.exp_result)

    def end(self, _, suffix=''):
        self.state.external_symbols.add('printf')

        format_parameters = []
        va_args = []
        for element in self.state.print_parameters:
            if isinstance(element, float) or element.startswith('%'):
                # Print number literal or local register
                format_parameters.append('%f')
                va_args.append('double {}'.format(element))
            elif element.startswith('"'):
                # Print string literal
                # Unescape and encode double quotes, encode "\"
                element = element[1:-1].replace('""', '\\22').replace('\\', '\\5C')
                format_parameters.append('%s')
                # Create a constant string
                str_id, str_len = self.const_string(element)
                va_args.append('i8* getelementptr inbounds ([{len} x i8], [{len} x i8]* {str_id}, i32 0, i32 0)'.format(len=str_len, str_id=str_id))

        format_string_id, length = self.const_string(' '.join(format_parameters) + suffix)
        self.state.append_instruction(
            'tail call i32 (i8*, ...) @printf(i8* getelementptr inbounds ([{len} x i8], [{len} x i8]* {identifier}, i32 0, i32 0), {va_args}) #0'.format(
                len=length,
                identifier=format_string_id,
                va_args=', '.join(va_args),
            ))
        self.state.print_parameters = []

    def end_with_newline(self):
        self.end(None, suffix='\\0A')
