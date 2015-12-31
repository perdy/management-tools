{%- extends 'full.tpl' -%}

{# HTML template that selectively hides code, with show/hide buttons. #}

{%- block header -%}
<!DOCTYPE html>
<html>
<head>

<meta charset="utf-8" />
<title>{{resources['metadata']['name']}}</title>

<script src="https://cdnjs.cloudflare.com/ajax/libs/require.js/2.1.10/require.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/jquery/2.0.3/jquery.min.js"></script>

{% for css in resources.inlining.css -%}
    <style type="text/css">
    {{ css }}
    </style>
{% endfor %}

<style type="text/css">
/* Overrides of notebook CSS for static HTML export */
body {
  overflow: visible;
  padding: 8px;
}

div#notebook {
  overflow: visible;
  border-top: none;
}

@media print {
  div.cell {
    display: block;
    page-break-inside: avoid;
  } 
  div.output_wrapper { 
    display: block;
    page-break-inside: avoid; 
  }
  div.output { 
    display: block;
    page-break-inside: avoid; 
  }
}

.showhide_button {
  
  font-size: 14pt;
}

.folded_code {
  display: none;
}
</style>

<script type="text/javascript">
function showhide(id) {
  $('#'+id).toggleClass('folded_code');
}
</script>

<!-- Custom stylesheet, it must be in the same directory as the html file -->
<link rel="stylesheet" href="custom.css">

<!-- Loading mathjax macro -->
{{ mathjax() }}

</head>
{%- endblock header -%}

{# There must be a better way of giving each code input an HTML ID.
   This is rather a hack using the primitives Jinja gives us.
#}
{% set code_cell_numbers = cycler(*range(nb.cells | count)) %}

{% block in_prompt -%}
{%- endblock in_prompt %}

{% block input %}
{% endblock input %}

{% block out_prompt -%}
{%- endblock out_prompt %}
