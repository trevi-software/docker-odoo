openerp.listview_images = function(instance) {

    /* Add a new mapping to the registry for image fields */
    instance.web.list.columns.add('field.image','instance.web.list.FieldBinaryImage');

    /* Define a method similar to the one for forms to render image fields */
    instance.web.list.Binary = instance.web.list.Column.extend({
    	/**
     	* Return a link to the binary data as an image
     	*
     	* @private
     	*/
	_format: function (row_data, options) {
            var placeholder = "/web/static/src/img/placeholder.png";
            var value = row_data[this.id].value;
            var img_url = placeholder;

            if (value && value.substr(0, 10).indexOf(' ') == -1) {
		/* Data inline */
		img_url = "data:application/octet-stream;base64," + value;
	    } else {
		/* Data by URI (presumably slow) */
		img_url = instance.session.url('/web/binary/image', {model: options.model, field: this.id, id: options.id});
            }
	    /* FIXME: move the 30px stuff to something templateable */
	    return _.template('<image src="<%-src%>" width="64px" height="64px"/>', {
		src: img_url,
	    });
	}
    });
}
