from compiler.tokenizer import tokenize, Token, L

def test_tokenizer_basics() -> None:
    # assert tokenize("if  3\nwhile") == ['if', '3', 'while']

    assert tokenize('aaa 123 bbb') == [
        Token(loc=L, type="identifier", text="aaa"),
        Token(loc=L, type="int_literal", text="123"),
        Token(loc=L, type="identifier", text="bbb"),
    ]

def test_tokenizer_operators_and_punctuation() -> None:
    src = 'aaa == { } + - * / % = != <= >= < > ; ,'
    expected = [
        Token(text="aaa", type="identifier", loc=L),
        Token(text="==", type="operators", loc=L),
        Token(text="{", type="punctuation", loc=L),
        Token(text="}", type="punctuation", loc=L),
        Token(text="+", type="operators", loc=L),
        Token(text="-", type="operators", loc=L),
        Token(text="*", type="operators", loc=L),
        Token(text="/", type="operators", loc=L),
        Token(text="%", type="operators", loc=L),
        Token(text="=", type="operators", loc=L),
        Token(text="!=", type="operators", loc=L),
        Token(text="<=", type="operators", loc=L),
        Token(text=">=", type="operators", loc=L),
        Token(text="<", type="operators", loc=L),
        Token(text=">", type="operators", loc=L),
        Token(text=";", type="punctuation", loc=L),
        Token(text=",", type="punctuation", loc=L),
    ]
    assert tokenize(src) == expected

def test_tokenizer_skips_comments() -> None:
    src = 'aaa 123 // this is a comment\nbbb # another comment'
    expected = [
        Token(text="aaa", type="identifier", loc=L),
        Token(text="123", type="int_literal", loc=L),
        Token(text="bbb", type="identifier", loc=L),
    ]
    assert tokenize(src) == expected

def test_tokenizer_if_statement() -> None:
    source = """if a < 10 then {
            print_int(3*x);  # this here is a comment
            }"""

    expected_tokens = [
        Token(loc=L, type="identifier", text="if"),
        Token(loc=L, type="identifier", text="a"),
        Token(loc=L, type="operators", text="<"),
        Token(loc=L, type="int_literal", text="10"),
        Token(loc=L, type="identifier", text="then"),
        Token(loc=L, type="punctuation", text="{"),
        Token(loc=L, type="identifier", text="print_int"),
        Token(loc=L, type="punctuation", text="("),
        Token(loc=L, type="int_literal", text="3"),
        Token(loc=L, type="operators", text="*"),
        Token(loc=L, type="identifier", text="x"),
        Token(loc=L, type="punctuation", text=")"),
        Token(loc=L, type="punctuation", text=";"),
        Token(loc=L, type="punctuation", text="}"),
    ]

    assert tokenize(source) == expected_tokens

def test_complex_tokenizer() -> None:
    src = """var i = 1;
        var s = 0;
        while i <= 5 do {
            s = s + i;
            i = i + 1;
        }
        s"""

    expected_tokens = [
        Token(loc=L, type="identifier", text="var"),
        Token(loc=L, type="identifier", text="i"),
        Token(loc=L, type="operators", text="="),
        Token(loc=L, type="int_literal", text="1"),
        Token(loc=L, type="punctuation", text=";"),
        Token(loc=L, type="identifier", text="var"),
        Token(loc=L, type="identifier", text="s"),
        Token(loc=L, type="operators", text="="),
        Token(loc=L, type="int_literal", text="0"),
        Token(loc=L, type="punctuation", text=";"),
        Token(loc=L, type="identifier", text="while"),
        Token(loc=L, type="identifier", text="i"),
        Token(loc=L, type="operators", text="<="),
        Token(loc=L, type="int_literal", text="5"),
        Token(loc=L, type="identifier", text="do"),
        Token(loc=L, type="punctuation", text="{"),
        Token(loc=L, type="identifier", text="s"),
        Token(loc=L, type="operators", text="="),
        Token(loc=L, type="identifier", text="s"),
        Token(loc=L, type="operators", text="+"),
        Token(loc=L, type="identifier", text="i"),
        Token(loc=L, type="punctuation", text=";"),
        Token(loc=L, type="identifier", text="i"),
        Token(loc=L, type="operators", text="="),
        Token(loc=L, type="identifier", text="i"),
        Token(loc=L, type="operators", text="+"),
        Token(loc=L, type="int_literal", text="1"),
        Token(loc=L, type="punctuation", text=";"),
        Token(loc=L, type="punctuation", text="}"),
        Token(loc=L, type="identifier", text="s"),
    ]