;
///////////////////////////
// Create an immediately invoked functional expression to wrap our code
(function() {

    // Define our constructor
    this.karyotype = function (options) {
        this.name = 'karyotype';
        this.version = '3.0';
        this.options = options || {};

        // constants
        this.constants = {};

        // defaults
        this.defaults = {};
        this.defaults.debug = false;
        this.defaults.id = 'karyotype';  // the id of the dom element
        this.defaults.margin = {top: 30, right: 80, bottom: 100, left: 50};
        // define width and height as the inner dimensions of the chart area.
        this.defaults.width = 500 - this.defaults.margin.left - this.defaults.margin.right;
        this.defaults.height = 500 - this.defaults.margin.top - this.defaults.margin.bottom;
        this.defaults.url = 'js/data/chromosomes.json';  // chromosome data
        this.defaults.showPositionOnHover = true;

        // callbacks
        this.defaults.onSelection = null;
        this.defaults.onSelecting = null;
        this.defaults.onHover = null;
        this.defaults.onHoverStart = null;
        this.defaults.onHoverStop = null;

        // a combination of defaults, but overriden by options
        this.settings = {};

        // generated data
        this.div = null;
        this.svg = null;
        this.plot = null;
        this.chromosomes = [];
        this.maxLength = 0;
        this.selectedData = null;
        this.xScale = null;
        this.yScale = null;
        this.yPositions = []; // cannot do invert on ordinal scales so keeping track
        this.currentPosition = null;
        this.hovering = false;

        // initialization
        console.log('attempting to call init');
        this.init();
    };


    karyotype.prototype.commafy = function (number) {
        return ("" + number).replace(/(^|[^\w.])(\d{4,})/g, function ($0, $1, $2) {
            return $1 + $2.replace(/\d(?=(?:\d\d\d)+(?!\d))/g, "$&,");
        });
    };

    /**
     * Get just the numeric or X or Y part of a chromosome string.
     *
     * @method stringToChromosome
     * @param {String} chromosomeStr a string representing a chromosome
     * @return {String} the numeric or X or Y portion of the chromosomeStr
     */
    karyotype.prototype.stringToChromosome = function (chromosomeStr) {
        let chr = null;
        if (chromosomeStr) {
            chr = chromosomeStr.trim();
            let re = /([A-W|Z|a-w|z|]*)\s*([\d|X|x|Y|y]*)/;
            let found = chr.match(re);
            if (found[2]) {
                chr = found[2];
            }
        }
        return chr;
    };

    /**
     * Set the selectedData value and call the onSelection method.
     *
     * @method selection
     * @param {String} chr the chromsome
     * @param {Number} start the start position
     * @param {Number} end the end position
     */
    karyotype.prototype.selection = function (chr, start, end) {
        this.selectedData = {'chr': chr, 'start': start, 'end': end};

        if (this.settings.onSelection != null) {
            this.settings.onSelection.call(this, this.selectedData);
        }
    };

    /**
     * Set the selectedData value and call the onSelecting method.
     *
     * @method selecting
     * @param {String} chr the chromsome
     * @param {Number} start the start position
     * @param {Number} end the end position
     */
    karyotype.prototype.selecting = function (chr, start, end) {
        this.selectedData = {'chr': chr, 'start': start, 'end': end};

        if (this.settings.onSelecting != null) {
            this.settings.onSelecting.call(this, this.selectedData);
        }
    };

    /**
     * Set the current position and call the onHover method.
     *
     * @method hover
     * @param {String} chr the chromsome
     * @param {Number} start the start position
     * @param {Number} end the end position
     */
    karyotype.prototype.hover = function (chr, position, coord) {
        this.currentPosition = {'chr': chr, 'position': position, 'str': chr + ':' +this.commafy(position)};

        if (this.settings.showPositionOnHover) {
            // update hover position
            let text = chr + ":" + this.commafy(position);
            d3.select('#hoverText')
                .attr('x', coord[0] - 20)
                .attr('y', coord[1] - 10)
                .text(text);

            let bbox = d3.select('#hoverText').node().getBBox();

            d3.select('#hoverRect')
                .attr('x', bbox.x - 5)
                .attr('y', bbox.y - 3)
                .attr('width', bbox.width + 10)
                .attr('height', bbox.height + 6);
        }

        if (this.settings.onHover != null) {
            this.settings.onHover.call(this, this.currentPosition);
        }
    };

    /**
     * Hover start event
     *
     * @method hoverStart
     */
    karyotype.prototype.hoverStart = function () {

        if (this.settings.showPositionOnHover) {
        }

        if (this.settings.onHoverStart != null) {
            this.settings.onHoverStart.call(this, this.currentPosition);
        }
    }

    /**
     * Hover stop event
     *
     * @method hoverStop
     */
    karyotype.prototype.hoverStop = function () {
        if (this.settings.showPositionOnHover) {
            d3.select('#hoverRect')
                .attr('x', -1000)
                .attr('y', -1000);
            d3.select('#hoverText')
                .attr('x', -1000)
                .attr('y', -1000);
        }

        if (this.settings.onHoverStop != null) {
            this.settings.onHoverStop.call(this, this.currentPosition);
        }
    };

    karyotype.prototype.setURL = function(url) {
        console.log(url);
        this.settings.url = url;
        this.init();
    };

    /**
     * Initialize the widget.
     *
     * @method init
     */
    karyotype.prototype.init = function () {
        console.log('init');
        // reference self
        var that = this;

        // set the settings
        this.settings = {};
        for (key in this.defaults) {
            if (key in this.options) {
                this.settings[key] = this.options[key];
            } else {
                this.settings[key] = this.defaults[key];
            }
        }

        if ($('#' + this.settings.id).length) {
            // element exists
            this.div = $('#' + this.settings.id);
        } else {
            alert('No element found with id of "#' + this.settings.id + '"');
            return;
        }

        d3.json(this.settings.url, function (e, data) {
            let chroms = [];
            for (c in data.chromosomes) {
                if (c !== 'MT') {
                    chroms.push(data.chromosomes[c]);
                }
            }

            var currentChromosome = null;
            that.maxLength = d3.max(chroms, function (d) {
                return d.length;
            });

            var xScale = d3.scale.linear().domain([0, that.maxLength]).range([0, that.settings.width]);
            var yScale = d3.scale.ordinal().domain(d3.range(chroms.length)).rangeBands([0, that.settings.height], .5);
            that.xScale = xScale;
            that.yScale = yScale;
            var svgChromG = [];

            let w = that.settings.width + that.settings.margin.left + that.settings.margin.right;
            let h = that.settings.height + that.settings.margin.top + that.settings.margin.bottom;


           that.svg = d3.select('#' + that.settings.id)
               .append("div")
               .classed("svg-container", true) //container class to make it responsive
                .append("svg")
                .attr("xmlns", "http://www.w3.org/2000/svg")
                .attr("version", 1.1)
                .attr("id", "svg_" + that.settings.id)
   //responsive SVG needs these 2 attributes and no width and height attr
   .attr("preserveAspectRatio", "xMinYMin meet")
               .attr("viewBox","0 0 " + w + " " + h)
   //class to make it responsive
   .classed("svg-content-responsive", true);

//                .attr("width", that.settings.width + that.settings.margin.left + that.settings.margin.right)
  //              .attr("height", that.settings.height + that.settings.margin.top + that.settings.margin.bottom);

            that.plot = that.svg.append("g")
                .attr("id", "translated_rect")
                .attr("transform", "translate(" + that.settings.margin.left + "," + that.settings.margin.top + ")");

            d3.select('#' + that.settings.id)
                .on('mousemove', function (evt) {
                    var pos = d3.mouse(this);
                    pos[0] -= that.settings.margin.left;
                    pos[1] -= that.settings.margin.top;

                    if ((pos[0] < 0) ||
                        (pos[0] > that.settings.width) ||
                        (pos[1] < 0) ||
                        (pos[1] > that.settings.height)) {

                        if (that.hovering) {
                            that.hoverStop();
                        }
                        that.hovering = false;
                    } else {
                        if (!that.hovering) {
                            that.hoverStart();
                        }
                        that.hovering = true;

                        var chromosome = null;
                        // how do we find the chromosome easily?
                        for (var c in chroms) {
                            chromosome = chroms[c].chromosome;
                            if (yScale(c) + yScale(0) + (yScale(0) / 2) > pos[1]) {
                                break;
                            }
                        }


                        that.hover(chromosome, Math.floor(xScale.invert(pos[0])), pos);
                    }
                });

            var xAxis = d3.svg.axis()
                .scale(xScale)
                .orient("bottom")
                .tickValues(that.getXAxisTickValues)
                .tickFormat(function (d) {
                    return (d / 1000000) + ' Mb';
                });

            that.plot.append("g")
                .attr("class", "x-axis")
                .attr("transform", "translate(0," + (that.settings.height) + ")")
                .call(xAxis);

            that.plot.selectAll(".x-axis text")  // select all the text elements for the xaxis
                .style("text-anchor", "end")
                .attr("transform", function (d) {
                    return "translate(" + -this.getBBox().height + "," + this.getBBox().height + ")rotate(-90)";
                });

            var yAxis = d3.svg.axis()
                .scale(yScale)
                .orient("left")
                .tickValues(function () {
                    var vals = [];
                    jQuery.each(chroms, function (i, val) {
                        vals.push(i);
                    });
                    return vals;
                })
                .tickFormat(function (d) {
                    return chroms[d].chromosome;
                });

            that.plot.append("g")
                .attr("class", "y-axis")
                .call(yAxis);

            that.plot.append("g")
                .attr("class", "x-grid")
                .attr("transform", "translate(0," + (that.settings.height) + ")")
                .call(d3.svg.axis().scale(xScale).orient("bottom").tickValues(that.getXAxisTickValues).tickFormat("").tickSize(-that.settings.height, 0, 0));

            jQuery.each(chroms, function (i, val) {
                // create a new grouping for each chromosome
                var currentChromG = that.plot.append("g").attr("id", "chrom_" + val.chromosome);

                svgChromG.push(currentChromG);
                val.chrIndex = i;
                val.chrNum = i + 1;
                that.chromosomes.push(val);

                var chrBoxes = [];

                jQuery.each(val.karyotypes, function (j, obj) {
                    obj.chrIndex = i;
                    obj.chrNum = i + 1;
                    chrBoxes.push(obj);
                });

                // add each stain section
                currentChromG.selectAll("rect")
                    .data(chrBoxes)
                    .enter()
                    .append("rect")
                    .style("stroke-width", .5)
                    .style("stroke", "black")
                    //.attr('pointer-events', 'pointermove')
                    .attr("height", yScale.rangeBand())
                    .attr("x", function (d, i) {
                        return xScale(d.seq_region_start);
                    })
                    .attr("y", function (d, i) {
                        return yScale(d.chrIndex);
                    })
                    .attr("width", function (d, i) {
                        return xScale(d.seq_region_end - d.seq_region_start);
                    })
                    .attr("fill", function (d) {
                        return that.getStainColor(d.stain);
                    });


                // add a rect the length of the chromosome to use for hilites
                var hl = currentChromG.append("g").attr("id", "chrhl_" + val.chrNum);

                var brushG = currentChromG.append("g").attr("id", "g_" + val.chrNum).attr("class", "x brush");
                var brush = d3.svg.brush();

                brushG.datum({brush: brush});

                brush.x(d3.scale.linear().domain([0, that.chromosomes[i].length]).range([0, xScale(that.chromosomes[i].length)]));
                brush.on("brushstart", function (p) {
                    brush.x(d3.scale.linear()
                        .domain([0, that.chromosomes[i].length])
                        .range([0, xScale(that.chromosomes[i].length)]))

                    d3.selectAll(".x.brush")
                        .filter(function (d) { /*console.log(d, d.brush != brush);*/
                            return d.brush != brush;
                        })
                        .each(function (d) {
                            d3.select(this).call(d.brush.clear())
                        });

                }).on("brush", function (p) {
                    that.selecting(that.chromosomes[i].chromosome, Math.floor(brush.extent()[0]), Math.ceil(brush.extent()[1]));
                }).on("brushend", function (p) {
                    that.selection(that.chromosomes[i].chromosome, Math.floor(brush.extent()[0]), Math.ceil(brush.extent()[1]));
                });

                brushG.call(brush)
                    .selectAll("rect")
                    .attr("y", yScale(that.chromosomes[i].chrIndex))
                    .attr("height", yScale.rangeBand());

            }); // end each data.chromosomes


            var g = that.plot.append("g")
                .attr("id", "hoverGroup");
            g.append("rect")
                .attr("id", "hoverRect")
                .style("stroke-width", 1)
                .style("stroke", "black")
                .style("fill", "#FFFFCC")
                .attr("height", 10)
                .attr("width", 10)
                .attr("x", -1000)
                .attr("y", -1000);
            g.append("text")
                .attr("id", "hoverText")
                .style("stroke", "black")
                .style("font-size", "10px")
                .style("font-family", "monospace")
                .text("");


        }); // end d3.json

    };

    /**
     * Get the stain/dye color.
     *
     * @method getStainColor
     * @param {String} stain one of (gneg, gpos33, gpos66, gpos10)
     * @return {String} the hexidecimal color representation
     */
    karyotype.prototype.getStainColor = function (stain) {
        if (stain === 'gneg') {
            return "#FFFFFF";
        }
        else if (stain === 'gpos25') {
            return "#C8C8C8";
        }
        else if (stain === 'gpos33') {
            return "#BBBBBB";
        }
        else if (stain === 'gpos50') {
            return "#999999";
        }
        else if (stain === 'gpos66') {
            return "#888888";
        }
        else if (stain === 'gpos75') {
            return "#777777";
        }
        else if (stain === 'gpos100') {
            return "#444444";
        }
        else if (stain === 'acen') {
            return "#FFEEEE";
        }
        return "#000000";
    };

    /**
     * Get an array of values starting with 0 and incrementing by 20000000 up to
     * 200000000
     *
     * @method getXAxisTickValues
     * @return {Object} an array of integer values
     */
    karyotype.prototype.getXAxisTickValues = function () {
        var vals = [];
        vals.push(0);
        while (vals[vals.length - 1] < 260000000) {
            vals.push(vals.length * 20000000);
        }
        return vals;
    };

    /**
     * Remove all the highlights
     *
     * @method setHighlight
     * @param {Object} data a simple json object representing a location with
     *     attributes chr, start, end
     */
    karyotype.prototype.setHighlight = function (data) {
        var chromosome = null;

        jQuery.each(this.chromosomes, function (i, val) {
            if (val.id === data.chr) {
                chromosome = val;
            }
        });

        if (chromosome == null) {
            return;
        }

        var start = Math.min(data.start, data.end);
        var end = Math.max(data.start, data.end);

        if (start > chromosome.end) {
            start = 0;
            end = 0;
        } else if (end < chromosome.start) {
            start = 0;
            end = 0;
        } else {
            start = Math.max(start, chromosome.start);
            end = Math.min(end, chromosome.end);
        }

        var hl = {'chr': chromosome.chrNum, 'start': start, 'end': end};
        var id = "hl_" + chromosome.chrNum + "_" + start + "_" + end;

        d3.select("#" + id).remove();

        d3.select("#chrhl_" + chromosome.chrNum)
            .append("rect")
            .attr("id", "hl_" + chromosome.chrNum + "_" + start + "_" + end)
            .attr("y", this.yScale(chromosome.chrIndex))
            .attr("x", this.xScale(start))
            .attr("height", this.yScale.rangeBand())
            .attr("width", this.xScale(end - start))
            .attr("class", "highlight");

        d3.select("#chrhl_" + chromosome.chrNum)
            .append("rect")
            .attr("y", this.yScale(chromosome.chrIndex) - 10)
            .attr("x", this.xScale(start) - 10)
            .attr("height", this.yScale.rangeBand() + 20)
            .attr("width", this.xScale(end - start) + 20)
            .style("stroke", 'blue')
            .style("stroke-opacity", 1)
            .style("fill", "none")
            .transition()
            .duration(750)
            .ease(Math.sqrt)
            .attr("y", this.yScale(chromosome.chrIndex))
            .attr("x", this.xScale(start))
            .attr("height", this.yScale.rangeBand())
            .attr("width", this.xScale(end - start))
            .style("stroke-opacity", 1e-6)
            .remove();

    };

    /**
     * Remove all the highlights
     *
     * @method clearHighlights
     */
    karyotype.prototype.clearHighlights = function () {
        d3.selectAll(".highlight").remove();
    };


    /**
     * Sets the function callback upon a complete selection.
     *
     * @method onSelection
     * @param {Function} callback a function to call upon selection
     */
    karyotype.prototype.onSelection = function (callback) {
        this.settings.onSelection = callback;
    };

    /**
     * Sets the function callback while selction occurs.
     *
     * @method onSelecting
     * @param {Function} callback a function to call while selction is occuring
     */
    karyotype.prototype.onSelecting = function (callback) {
        this.settings.onSelecting = callback;
    };

    /**
     * Sets the function callback while hover occurs.
     *
     * @method onHover
     * @param {Function} callback a function to call while hover is occuring
     */
    karyotype.prototype.onHover = function (callback) {
        this.settings.onHover = callback;
    };

    /**
     * Get the selected coordinate
     *
     * @return {Object} the selected location with attributes chr, start, end
     */
    karyotype.prototype.getSelection = function () {
        return this.selectedData;
    };

    /**
     * Set the selection if it is valid by using a brush to paint the selection.
     * This will also call the onSelection method (if set).
     *
     * @method setSelection
     * @param {Object} data a simple json object representing a location with
     *     attributes chr, start, end
     */
    karyotype.prototype.setSelection = function (data) {
        var chromosome = null;

        jQuery.each(this.chromosomes, function (i, val) {
            if (val.id === data.chr) {
                chromosome = val;
            }
        });

        if (chromosome == null) {
            return;
        }

        var start = Math.min(data.start, data.end);
        var end = Math.max(data.start, data.end);

        if (start > chromosome.end) {
            start = 0;
            end = 0;
        } else if (end < chromosome.start) {
            start = 0;
            end = 0;
        } else {
            start = Math.max(start, chromosome.start);
            end = Math.min(end, chromosome.end);
        }

        // this is inefficient, but it works
        // select all brushes that aren't the chromosome and clear them
        d3.selectAll(".x.brush")
            .filter(function (d) {
                return this != d3.select("#g_" + chromosome.chrNum)[0][0];
            })
            .each(function (d) {
                d3.select(this).call(d.brush.clear())
            });

        // select the brush chromosome and set it's extent
        d3.selectAll(".x.brush")
            .filter(function (d) {
                return this === d3.select("#g_" + chromosome.chrNum)[0][0];
            })
            .each(function (d) {
                d3.select(this).call(d.brush.extent([start, end]));
            });

        this.selection(chromosome.id, start, end);
    };

    /**
     * Attempt to convert a string representing a location into it's numeric value
     *
     * @method convertCoordinateBases
     * @param {String} coordinateStr a string representing a coordinate, could be
     *     numeric or string with Mb in it
     * @return {Number} the numeric value of the string
     */
    karyotype.prototype.convertCoordinateBases = function (coordinateStr) {
        var num = null;
        if (coordinateStr) {
            var coord = coordinateStr.trim();
            var re = /(\d*\.?\d*)\s*(\w*)/;
            var found = coord.match(re);
            var multiplier = 1;
            if (found) {
                if (found[2]) {
                    // base specified
                    num = parseFloat(found[1]);
                    if (found[2] === 'Mb') {
                        num = Math.ceil(num * 10000000);
                    }
                } else {
                    // no base specified
                    num = parseFloat(found[1]);

                    // if it's a floating point number we will assume it's Mb and need to
                    // multiply by 1,000,000
                    if (found[1].indexOf('.') >= 0) {
                        num = Math.ceil(num * 1000000);
                    }
                }
            }
        }
        return num;
    };

    /**
     * Convert a string into a location.
     *
     * @method stringToLocation
     * @param {String} locationStr the location string representing a genomic
     *     location such as "1:752317-7615322"
     * @return {Object} a simple json object with chr, start, and end attributes,
     *     such as {'chr':'1', 'start':752317, 'end':7615322}
     */
    karyotype.prototype.stringToLocation = function (locationStr) {
        var location = {'chr': null, 'start': null, 'end': null};
        if (locationStr) {
            var re = /^(\w*)(\s*[-:\s]\s*)(\d*\.?\d*\s*\w*)(\s*[-:\s]\s*)(\d*\.?\d*\s*\w*)$/;
            var found = locationStr.match(re);

            if (found && (found.length == 6)) {
                var chr = stringToChromosome(found[1]);
                if (chr) {
                    location['chr'] = chr;
                    location['start'] = this.convertCoordinateBases(found[3]);
                    location['end'] = this.convertCoordinateBases(found[5]);
                }
            }
        }
        return location;
    };

}());

